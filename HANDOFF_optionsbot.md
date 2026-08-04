# HANDOFF — options-bot lane (C1, C2, C3, C4, C6, O8)

Owner: `options-bot lane`. Source: `VALQUO_EDGE_AUDIT.md` Part XIII (C1-C7) and Part IV (O8).
Scope: `options-bot/**` only. `valuation/**` untouched.

---

## 0. PRE-REGISTERED THRESHOLDS — written BEFORE any run

These are committed here first, in writing, and are not re-derived after seeing a number.

### O8 — index variance risk premium (SPY / QQQ / IWM put credit spreads)

Primary window **2018-01-01 to 2025-12-31**. Pre-2018 is reported separately and is
**not permitted to change the verdict** (Dew-Becker et al. 2025-17: the index VRP declined
in the 2020s, so a 1990s-2010s number is a different regime, not more evidence).

The verdict rests on **SPY** — the deepest and tightest index chain, and the one the VRP
literature is actually about. QQQ and IWM are reported as robustness, not as votes.

* **ADOPT** (i.e. proceed to O8's stage 2, porting the arm to real option chains) requires
  ALL FOUR on SPY over the primary window, default config (vol-scaled sizing ON, weekly
  expiries, 20-delta, $5 wide, 35 DTE):
  1. total return > 0
  2. **excess Sharpe >= 0.50** (a fat-left-tail premium-selling strategy has to clear cash
     by a real margin before real-chain work is worth paying for)
  3. no ruin halt
  4. COVID-crash window (2020-02-15 to 2020-04-30) return >= **-25%**
* **REJECT** if SPY total return <= 0, or excess Sharpe < 0, or the run halts for ruin.
* Anything in between is **INCONCLUSIVE** and gets reported as such, not rounded up.

### C1 — backtest the model that ships

The threshold is **the one already compiled into `screener/backtest_engine.py:summarize()`**,
chosen deliberately so it cannot be tuned after the fact — it predates this session:
`edge = (mean IC > 0 AND |IC t| >= 2.0) AND (in-sample mean IC > 0 AND out-of-sample mean IC > 0)
AND (top-minus-bottom quintile spread net of 8 bps/side > 0)`.

* **ADOPTED** = the LIVE model (`scoring.py`) clears that bar on the point-in-time panel.
* **REJECTED** = it does not.
* Reported alongside: the SAME statistic for the discarded inline 6-factor model, so the
  size of the C1 defect is quantified rather than asserted.
* If the live scorer cannot be replayed point-in-time at all, **that is the finding** and it
  is recorded as such (the audit's own instruction), not papered over.

### C2 — universe

No statistical threshold; this is a correctness item. The deliverable is a universe whose
**median market cap sits below the screener's own `MARKET_CAP_CEILING` ($10B)**, versus the
current one. Pass = median cap of the backtest universe < $10B and > 50% of names below the
ceiling. Reported with the before/after number.

### C3 — `--bots reversion`

Correctness item, no statistic. Pass = the flag can no longer accept an argument, run nothing,
and print success. Verified by an executable test.

### C4 — the tracking loop

Pass = (a) something calls `store.update_returns` on a schedule, (b) `run_review` refuses to
run on an all-NULL table, and (c) the guard is exercised by a test that fails against the old
code. Threshold for the review to run at all: **>= `SELF_REVIEW_MIN_SAMPLE` (40) rows with a
non-NULL realized return**, and non-NULL fraction >= 50% of rows whose horizon has closed.

### C6 — three undeployed fixes

Decision item. Pass = each of the three is in exactly one of two states — deployed, or deleted
and recorded — and none is left in the third state ("fixed in repo, not deployed").

---

---

# READ THIS FIRST — a LIVE bug, found while doing C1

## The insider component of the live screener is a constant. It has always been.

Not a backtest artefact. This is in the deployed path, right now.

`filings.recent.primaryDocument` for a Form 4 is EDGAR's **XSL-RENDERED** view —
`xslF345X03/ownership.xml` — which serves **HTML**, not XML. Measured across the
**370,681** Form 4 filings indexed for the C1 backtest: **99.3% carry an `xsl`
prefix** (xslF345X01 through X06; the largest, X03, accounts for 232,281).

`edgar.get_insider_txns` built exactly that URL. `_parse_form4_xml` called
`ET.fromstring` on the HTML, raised `ParseError`, **caught it, and returned `[]`**.
And `scoring.insider_score([])` is *documented* to mean "fetched, nothing
qualifying" — so it returns a confident, neutral **50.0**.

**Every name, on every run, scored exactly 50 on insider.** That component
carries **20% of the Established weight and 30% of the Speculative weight**.

Measured directly before the fix: **597 documents fetched, 597 parsed to zero
transactions, none non-empty.** After the fix, Alcoa's five most recent Form 4s
parse to five real transactions with named insiders, codes and dollar values
(`Reed Matthew T`, code `S`, $215,372).

Two things make this worth leading with:

* **It is the same defect the project already found once and wrote up.** The
  record says of `dcf_upside`: *"a 35% weight that is a constant is not a factor,
  it is a rounding error with extra steps."* That one was a missing computation
  and was found by someone going looking. This one **hid behind an exception
  handler**, which produces identical symptoms and is much harder to see.
* **Returning `[]` for a fetch failure is what let it survive.** `insider_score`
  is built on a careful three-way distinction — `None` means "not fetched" and
  renormalizes away, `[]` means "looked, found nothing" and scores a real neutral
  50. Collapsing a total fetch failure into the second bucket made the failure
  indistinguishable from an observation. **A silent `except` that returns the
  same value as success is not error handling.**

**Fixed.** `edgar.raw_form4_doc()` strips the renderer prefix at both URL
construction sites — the live `get_insider_txns` and the backtest's
`form4_index` — and the `ParseError` path now logs a WARNING stating it is a
FETCH error rather than an empty filing. 10 tests
(`screener/tests/test_form4_url.py`), including one that asserts five DIFFERENT
filings through the broken path all score exactly 50.0, because zero
cross-sectional dispersion is what a constant looks like in a cross-section.

**What this means for the record.** Every historical statement about the live
screener's insider component describes a constant. The audit's C1 note that "the
insider component has therefore never been backtested in any form" is true, and
understated: it was also never *computed* in production. Nothing that has ever
been said about insider signal quality in this system rests on data.

**→ This should ship.** It is a one-line behavioural change in the live scorer's
largest single non-value input, and it is on `main` in this lane's branch.

---

## A correction to the work order, found while doing it

**C3 does not live where the audit says it lives.** The entry points at
`options-bot/screener/run_backtest.py`; the `--bots` flag is in
`options-bot/quant_bots/scripts/run_backtest.py`. Two different files, same
basename. `check_lanes.py` inherited the same mapping and therefore reported a
HARD collision between C1, C2 and C3 that does not exist — C3 shares no file with
either. It was still done in the prescribed order, so nothing rests on this, but
the dependency map should be corrected before someone parallelises on it.

Everything else in the audit's Part XIII checked out against the code, and two
of the items are worse than described. Noted per item below.

---

# O8 — index variance risk premium · INCONCLUSIVE (SPY) / REJECTED (QQQ, IWM)

Full numbers, cost decomposition and caveats: **`options-bot/INDEX_VRP_RESULTS.md`**.
Raw stats + provenance for all six runs: `options_backtest/index_vrp_summary.json`.

**Committed threshold** (written first, §0): ADOPT needs SPY total return > 0 AND
excess Sharpe >= 0.50 AND no ruin halt AND COVID-window loss >= -25%. REJECT on
total return <= 0, or excess Sharpe < 0, or a ruin halt. Between = INCONCLUSIVE.

**Why no result existed.** Two defects, both in the code, neither about data
availability — so "nobody got round to running it" was not the reason:

1. **Stooq, the script's only data source, no longer serves scripts.** Bare
   request → HTTP 404; browser User-Agent → HTTP 200 carrying a JavaScript
   verification page. `csv.DictReader` parses that HTML into zero rows without
   raising, so the script's own error path reported "could not fetch required
   data" — a live-but-blocked feed presenting as missing data.
2. **It crashed on save, after printing the report.** `json.dumps` cannot encode
   the `date` objects on every `Trade`, so a fully successful run raised
   `TypeError` and left nothing on disk.

Fixed with a source chain (Stooq → **Cboe**, the authoritative publisher of
VIX/VXN/RVX and the only free source of ^RVX → **yfinance** for the ETFs and
^IRX) and `default=str`. The source used is now recorded in the results JSON.
**The engine itself needed no change** — the audit's read of it was accurate.

**What was run.** SPY/QQQ/IWM, 2018-01-01→2025-12-31, default config
(20-delta, $5 wide, 35 DTE, 50%/2x/21-DTE exits, vol-scaled 2% sizing, weekly
expiries, $100k). Pre-2018 run separately: SPY from 1993, QQQ/IWM from 2009
(VXN/RVX start 2009-09).

**The numbers.**

| primary window | SPY | QQQ | IWM |
|---|---|---|---|
| Total return | +31.54% | +3.25% | −38.40% |
| **Excess Sharpe** | **0.14** | **−0.05** | **−0.56** |
| Max drawdown | −23.2% | −33.3% | −46.8% |
| Trades / win rate | 1,905 / 76.0% | 1,907 / 75.9% | 1,892 / 70.2% |
| COVID / 2022 | −8.05% / −19.89% | −5.62% / −30.32% | −8.56% / −11.40% |

Pre-2018 excess Sharpe: SPY −0.54, QQQ −0.57, IWM −0.10 — **worse than the
primary window on all three.** The audit's caveat (Dew-Becker et al.: the index
VRP declined in the 2020s) predicts the older window should look *better*. It
does not. That is not evidence the VRP rose; it is the cost model biting hardest
in the low-VIX 2013–2017 regime, where the modelled credit is smallest and the
per-contract cost is fixed.

**Verdicts.** SPY **INCONCLUSIVE** (fails ADOPT at 0.14 vs 0.50; does not meet
any REJECT condition). QQQ and IWM **REJECTED**. Pre-2018 **REJECTED**, and not
used to set the verdict.

**Mechanism — this is a cost result, not a premium result.** Gross P&L is
positive in **all six** windows: the variance risk premium is real and it is
being captured. Execution then consumes **68% of it on SPY, 85% on QQQ, 201% on
IWM**, with slippage running ~3x commission. This is the same mechanism that
killed the single-name arm ($28 of a ~$65 credit crossing two spreads twice).
Index options do attack it — SPY's 0.68 is far better than single-name — but not
by enough.

**The ceiling, measured (post-hoc, NOT pre-registered).** SPY 2018–2025 with
slippage forced to $0.01/share/leg → excess Sharpe 0.39; $0.005 → 0.49;
**$0.00 → 0.62**. At literally free execution the strategy just clears the adopt
bar. **Recommendation: do not proceed to O8 stage 2 (real index chains).**
Better chain data would refine a number already known to top out below the
threshold at any achievable fill quality.

**Carry the caveats that cut FOR the strategy**: one IV per name-date means no
skew, so the modelled credit at the 20-delta put is too small and these numbers
are a **floor, not a level**; the stop model is pessimistic on slow losers. The
*gross-premium* finding is the robust half of this result and the *level* is the
soft half. Both point the same way, which is why this is a recommendation and
not a proof.

**What it unblocks.** O8 stage 2 is closed. The surviving lead is *structure*,
not underlying — fewer legs, fewer round trips, longer holds — and this test does
not license that; it would be a new pre-registration.

**Tests.** 8 new regression tests (`options_backtest/test_run_options_backtest.py`)
pin both defects, including that a 200-with-HTML-challenge is never counted as data.

---

# C3 — `--bots reversion` did nothing and reported success · FIXED

**Committed threshold:** the flag can no longer accept an argument, run nothing,
and print success; verified by an executable test.

**Verified against the code.** `main()` had `if "trend" in args.bots` and
`if "momentum" in args.bots` and nothing else, then printed
`"Backtests complete."` unconditionally. `--bots reversion` and `--bots options`
both fell straight through. One of four live strategies had never been
backtested in any form.

**The audit costed this "M to implement". It is XS.** `reversion` exposes exactly
the same three entry points as `momentum` — `compute_score_from_closes`,
`rank_and_select`, `strategy.build_target` — so `backtest_reversion` is the
momentum path with three imports changed.

**Shipped:** `backtest_reversion`; a `BACKTESTS` registry and an `UNSUPPORTED`
map (options, with the reason and a pointer to the backtest that *does* cover
it); validation that exits non-zero **before** any credential lookup or network
call; and a closing line that names which bots actually ran. The reversion
closure builds its price map from `selection.all_prices` rather than
`longs + shorts` — the shape that caused FIXES.md #1.

**Verdict: ADOPTED (correctness).** 6 tests
(`quant_bots/tests/test_backtest_cli.py`), including one that reads
`deploy/*-bot.service` and fails if a deployed bot is neither backtestable nor
explicitly unsupported — so a fifth strategy cannot repeat this silently.

**What it unblocks.** The reversion bot can now be backtested at all. It has NOT
been run here: `Backtester` needs `TRADIER_TOKEN` + `TRADIER_ACCOUNT_ID` for
history, and the run writes equity curves into the bots' state tree. That is a
live-credential job on Don's box, not a research run — **→ hand the actual
reversion backtest to Cowork / Don's machine.**

---

# C4 — the tracking loop was wired to nothing · FIXED

**Committed threshold:** (a) something calls `store.update_returns` on a
schedule, (b) `run_review` refuses an all-NULL table, (c) a test that fails
against the old code. Review may run only at >= `SELF_REVIEW_MIN_SAMPLE` (40)
rows with a realized return AND >= 50% non-NULL.

**Verified against the code, and it is worse than "nothing calls them".**
`store.update_returns`, `prices.benchmark_return`, `config.BENCHMARKS` and
`config.TRACK_HORIZONS_DAYS` were all implemented and unreferenced — confirmed.
But `run_review` had **no guard at all**: the audit says "its only guard is a row
count", and even that was not there. `SELF_REVIEW_MIN_SAMPLE = 40` sat in
`config.py` with a comment explaining that NULL rows must not count toward it,
and **nothing read the constant**. So the review ran unconditionally on a table
of NULLs.

**Shipped:**
* `prices.forward_return_from(symbol, since_date, sessions, ...)` — session
  arithmetic, returning a status that keeps `NOT_CLOSED`, `DELISTED` and
  `NO_DATA` distinct. The important one: an unelapsed horizon returns
  `NOT_CLOSED` and the row stays NULL for a later pass. Writing 0.0 there would
  fabricate a flat observation, and it would look exactly like a real one.
* `pipeline.update_track_returns(store, ...)` — fills every horizon, one price
  history per name (not per name-horizon), and is idempotent so it can be run on
  a cron independently of the daily scan (`python pipeline.py --update-returns`).
  Called FIRST in `run_daily`, inside a `try`, so a later crash still advances
  the track record — the one dataset here that cannot be rebuilt after the fact.
* Delisting is handled rather than dropped: a series that stops inside the
  horizon and does not resume within `DELISTING_GRACE_DAYS` freezes its last
  observed return and sets `delisted`. Dropping names that stopped trading is
  precisely how a track record lies about itself.
* Benchmarks are anchored **at the run date**. `prices.benchmark_return(sym, n)`
  measures the last `n` sessions — i.e. from today — and comparing a 2021 pick's
  forward return against the benchmark's most recent 30 sessions is not a
  comparison. A test pins this by feeding the pick and the benchmark the same
  synthetic series and asserting the two logged numbers are identical.
* `pipeline.review_readiness(store)` + new `config.MIN_TRACK_RETURN_COVERAGE`.
  Two conditions, because either alone is satisfiable by a dead loop: a COUNT
  (an old table that stopped being filled still clears it) and a RATE (a loop
  that silently stops filling now fails the review instead of quietly shrinking
  the sample). `run_review` posts the skip reason and returns `False`.

**Verdict: ADOPTED (correctness).** 18 tests
(`screener/tests/test_track_loop.py`), every one of which fails against the
pre-C4 code. Includes the exact pre-C4 scenario — 500 rows, 0 realized returns —
asserted to be refused, and a 500-row/60-filled case that clears the count and
fails the rate.

**What it unblocks.** This is the item with the highest long-run value in Part
XIII and the only one that starts a clock that cannot be started retroactively.
It is now capable of accruing dated forward returns on real picks. **It has
accrued nothing so far and will show nothing for ~30 sessions.** Note the
honest limit: the loop can only fill rows that were *logged*, and every day the
daily scan did not run is gone permanently.

---

# C6 — three fixed bugs undeployed · CAUSE FOUND, PARTIALLY FIXED, ONE BLOCKER

**Committed threshold:** each of the three is in exactly one of two states —
deployed, or deleted and recorded — and none is left in the third state.

**The three fixes are all present in the repository.** Verified individually,
not by proxy: fix 1 (exit orders dropped in SIM) — `core.sim_execution.resolve_prices`
exists, both `RankedSelection` dataclasses carry `all_prices`, `core/backtest.py`
marks from `mark_prices`; fix 2 (reversion shorting oversold names) — verified
*behaviourally*, by feeding `rank_and_select` a 40-name all-oversold
cross-section and asserting it shorts nothing; fix 3 (options risk caps inert in
SIM) — `Jobs.sim_positions_view` cannot be checked from a clean clone, which is
itself the finding below.

**Why they are undeployed — the cause is mechanical, not forgetfulness.**

> `options/orchestrator/jobs.py:36`, `options/screener/screener.py:34` and
> `options/scripts/screen.py:27` import `data` / `data.earnings`. **No `data/*.py`
> is tracked anywhere in this repository.** The repo-ROOT `.gitignore` line 26 is
> a bare `data/` — added for the main Valquo tree's licensed Sharadar exports,
> which genuinely must never be committed — and a gitignore pattern whose only
> slash is the trailing one matches at **every depth**, so it also excluded
> `options-bot/quant_bots/data/` when this subproject was added later.
> `quant_bots/.gitignore` ignores only `data/cache/`, `data/state/`,
> `data/journal/`, i.e. its author intended the package to be tracked. The root
> file wins.

Verified consequences, both reproduced:
* `cd options && python -m unittest discover` collects **53 of 181** tests and
  fails with **14x `ModuleNotFoundError: No module named 'data'`**.
* `deploy/deploy.sh` step 4 treats a failing options suite as fatal and `die`s
  **before** step 6 restarts any service. **The git-based deploy path cannot
  complete at all.**

That is sufficient to explain "fixed in repo, not deployed" without anyone
forgetting anything. It is also consistent with the record: `deploy.sh`
explicitly replaced a zip-and-scp flow, a zip does not consult `.gitignore`, and
`STATUS.md` reports 181 options tests "verified from a clean zip extract".

**A second, independent reason the state was invisible.** `FIXES.md` says "Test
counts changed. If you see the old numbers after a deploy, the old code is still
there." `deploy.sh` encoded that as `EXPECTED_CORE_TESTS=106` while the suite had
grown to 148 — two generations stale — and it is a `-lt` **warning that continues
anyway**. The one freshness signal the deploy had could not fire.

**Shipped (what is fixable from here):**
* `quant_bots/.gitignore` re-includes the source package (`!data/` — a deeper
  gitignore overrides a shallower one, and the directory itself must be
  un-excluded before anything inside it can be) and re-ignores every state
  subdirectory **by name**, so re-including `data/` does not start committing sim
  books and reports.
* `quant_bots/deploy/preflight.py` — checks that every bot package actually
  imports, and checks each FIXES.md fix **by symbol and by behaviour** rather than
  by a test count standing in for it. It names the `data` failure and prints the
  exact `scp` to fix it, instead of 14 opaque ImportErrors that read like a broken
  test environment. A deploy that aborts for an undecodable reason is a deploy
  that quietly stops happening.
* `deploy.sh` runs the preflight and `die`s on failure, before any restart.
* `EXPECTED_CORE_TESTS` 106 → 163, plus a test that makes the stale-constant bug
  self-detecting (the constant may never drift more than 12 tests behind reality).

**Verdict: the three fixes are ADOPTED-in-repo and still UNDEPLOYED**, and the
third state the audit warned about is now detected rather than assumed.

**BLOCKER — needs Don, one command.** The `data/*.py` sources exist only on the
Oracle box. The box is demonstrably live (`quant_data.tgz` carries journals
through 2026-07-31 and a correlation report dated 2026-08-02, owned by `ubuntu`),
so the files are there. Nothing here can reconstruct them — `EarningsCalendar`
has real behaviour (`unknown_means_safe`) and inventing an earnings filter that
silently lets names through would be worse than the gap. From a machine with the
key:

```
scp -r ubuntu@BOX:~/quant_bots/data/*.py <repo>/options-bot/quant_bots/data/
git add options-bot/quant_bots/data && git commit
python3 deploy/preflight.py       # must print PREFLIGHT OK
bash deploy/deploy.sh
```

Until that lands, **the options bot cannot be deployed from this repository, and
whatever is running on the box is code that no clone can reproduce.** That
second half is the part worth worrying about.

---

# C2 — the backtest universe was the inverse of the target · FIXED

**Committed threshold:** median market cap of the backtest universe below the
screener's own `MARKET_CAP_CEILING` ($10B), and >50% of names under it.

**Verified, and it is stronger than the audit states.** The audit says the
universe was "the exact inverse of the target". It was worse: **the intersection
was EMPTY.** EDGAR's `company_tickers.json` really is ordered by market cap
descending — checked directly, not inferred. Entries 1-10 are NVDA, AAPL, GOOGL,
MSFT, AMZN, AVGO, META, TSLA, MU, BRK-B; entries 290-300 are NKE, O, MET, CTVA,
COR, OKE, TEL, GWLIF, MPLX, FANG. Not one of the 300 is within an order of
magnitude of a $10B ceiling, so **zero of the tested names could ever have been
held by the strategy** except through the top-3-rank override.

**Result.**

| | old universe | corrected universe |
|---|---|---|
| Names | 300 | **1,017** |
| Median market cap | the 300 largest US filers | **$3.85B** |
| p25 / p75 | — | $2.19B / $6.59B |
| At or under the $10B ceiling | **0%** | **100.0%** |

Gate rejections on the way there (67,712 candidate rows → 42,342 kept):
`above_10B_ceiling=15,191`, `no_market_cap=8,737`, `below_liquidity_floor=1,280`,
`price_below_1=162`. The cap gate is genuinely point-in-time — shares
outstanding known on the date times that date's close.

**Verdict: ADOPTED (correctness).** `--universe legacy` still reproduces the old
universe for comparison.

**What is NOT fixed.** The candidate pool is still today's EDGAR filer list, so
delisted names are structurally absent and the panel stays survivorship-biased.
The point-in-time gate removes the LOOK-AHEAD selection only. Free data cannot
do better; **audit item C5 (the Sharadar mirror) is the only thing that can**, and
until it runs every number below is an upper bound.

---

# C1 — backtest the model that ships · REJECTED (both models)

**Committed threshold** (§0, and deliberately the rule already compiled into
`backtest_engine.summarize()`, which predates this session):
`mean IC > 0 AND |IC t| >= 2.0 AND both out-of-sample halves positive AND
top-minus-bottom quintile spread net of 8 bps/side > 0`.

**Verified against the code.** `run_backtest.py` never imported `scoring.py`. It
defined a six-factor model inline whose largest weight, `ey_sn`, does not exist
in the live model in any form — no bucket split, no gates, no value percentiles,
no insider, no DCF. The screener backtest did not measure the screener.

**Both models, one panel** — 2021-01→2025-06, 54 monthly rebalances, 21-session
horizon, 8 bps/side, corrected universe, IWM benchmark:

| | LEGACY inline model | LIVE model (minus insider) |
|---|---|---|
| Scored rows / names | 41,805 / 1,010 | 36,776 / 890 |
| Mean IC | 0.0168 | 0.0164 |
| **IC t** | **1.22** | **1.89** |
| Hit rate | 59% | 54% |
| **Top-minus-bottom, net** | **−0.46%** | **−0.23%** |
| Monotonic | No | No |
| OOS IC in / out | 0.0233 / 0.0102 | 0.0121 / **0.0207** |
| Quintile means Q1→Q5 | +1.87 / +1.03 / +0.98 / +1.20 / +1.72% | +1.63 / +1.06 / +1.04 / +1.20 / +1.72% |

**Verdict: REJECTED for both.** Each fails two of the three conditions — t below
2.0 and a negative net top-minus-bottom spread.

**Three findings that outlast the verdict:**

1. **The model nobody was testing is the sturdier one.** Nearly identical mean IC
   (0.0164 vs 0.0168) but **t 1.89 vs 1.22** — the same average signal with
   materially lower period-to-period volatility — and the live model's
   out-of-sample half is *stronger* than its in-sample half (0.0207 vs 0.0121)
   while the legacy model's decays (0.0102 vs 0.0233). The parallel model was
   therefore not merely a different model; it was a noisier one, and every
   historical number this system produced carried that extra noise.
2. **A positive IC with a NEGATIVE top-minus-bottom spread is the decisive
   failure, and it is not a contradiction.** Quintile returns are U-shaped in
   both models: the WORST-scored quintile has the highest forward return
   (+1.87% / +1.63%) and the best-scored is second (+1.72%). The rank
   correlation is being earned in the middle of the distribution, not at the
   tails — which is precisely where a long-only top-decile book trades. Any
   future work here should report both; the IC alone would have read as
   encouraging.
3. **`no_market_cap` rejects 8,737 rows (12.9%)** — point-in-time shares
   outstanding are missing that often on the EDGAR path. That is a coverage
   problem worth its own look before anyone re-runs this.

## Insider: still not measured — and now the cost of measuring it is a number

The 20-30% of live weight the audit flags as never backtested is still never
backtested. This is the one part of the lane's scope I did not finish, and the
reason is quantitative, not a shrug.

**The machinery is built and tested.** `edgar.form4_index` walks the paginated
submissions shards — `filings.recent` is capped at ~1,000 filings of ALL types,
so for an active filer it can cover under a year, which makes it a live-screener
feed and not a history; nothing before this could replay the live insider input
at all. `panel_cache.insider_asof` replays "the six most recent Form 4s filed ON
OR BEFORE this date" and is pinned by 11 point-in-time tests, including that the
window actually MOVES with the date (a replay returning the same six filings
every month would look fine and be a constant) and that None ("not fetched",
renormalizes away) stays distinct from [] ("looked, found nothing", a neutral 50).

**Measured cost, not estimated.** The index walk ran to 482 of 1,017 gated
filers and reported the union of documents any (name, date) pair would request:

| filers indexed | documents queued |
|---|---|
| 300 | 35,163 |
| 375 | 44,233 |
| 450 | 52,132 |

That extrapolates to **~120,000 Form 4 documents** for the full universe. Sustained
document-fetch rate, measured over two minutes on an otherwise idle machine:
**43 documents/minute** (~1.4 s round trip — latency-bound, not bandwidth-bound;
`edgar._MIN_INTERVAL` of 0.12 s is nowhere near binding). That is **~46 hours** of
serial crawling.

So this is a scheduled job, not a session task, and running it unattended against
a public API for two days was not something to start and walk away from. The
cache is incremental and resumable — 482 filer indexes are already on disk, and
nothing already fetched is ever re-fetched.

**To finish it:**

```
cd options-bot/screener
EDGAR_USER_AGENT="..." python run_backtest.py --model live --universe target \
    --band 500 2000 --prefetch-only        # resumable; ~46h serial as written
EDGAR_USER_AGENT="..." python run_backtest.py --model both --universe target \
    --band 500 2000                        # then this is fast, all cached
```

**The obvious optimisation, deliberately not done here:** EDGAR permits ~10
req/s and we are achieving 0.7. A small thread pool in `panel_cache.form4_txns`
would cut this to a few hours. I did not add it because a concurrency bug against
a rate-limited public API fails by getting the IP blocked, and that is a bad thing
to discover unattended — it wants a deliberate run with someone watching.

Everything reported above is therefore the live model **minus** its insider
component, labelled that way in this file and in the report the script prints.

**One deliberate simplification, stated so it is not mistaken for an oversight:**
the live pipeline's `market_cap_eligible` lets a name past the $10B ceiling if it
ranks top-3 or shows an insider cluster. That override is applied AFTER ranking,
so reproducing it would make universe membership depend on the score — and then
the two models would be scored on two different universes, which is the one thing
C1 exists to prevent. The ceiling is a hard gate here instead.

## Two defects found while validating C1, both silent, both fixed

**(a) pandas was poisoning the live scorer.** `pit_data` correctly returns None
for a missing input, but the moment those values pass through a DataFrame pandas
stores them as float NaN, and every missing-data branch in `scoring.py` tests
`is None`. So NaN sailed through as PRESENT: `quality_score(op_margin=nan, ...)`
→ `_clip01(nan/0.25)` → nan → `_weighted()` counts it present → the whole
composite is NaN → **the name is dropped instead of renormalizing onto the inputs
it does have.** Silently, and without appearing in the skip tally. On a 60-name
slice: 89 rows unscored, of which the counter saw 19 and NaN ate the other 70.

The worse half: `classify_bucket` returns None for genuinely unknown
profitability because — per its own docstring — mapping a parser gap to
"speculative" turns a data problem into a strategy decision. NaN defeats that
exactly (`nan is not None` is True, `nan > 0` is False), so **every
profitability-unknown name was silently scored against loss-making growth
companies on a different factor set.** The transport layer re-introduced through
the back door the precise bug the live code had deliberately fixed.

Fixed by `_denan` at the panel→scorer boundary. Unscored rows now equal reported
skips exactly, and that is a test. 10 tests, including that 0.0 and False survive
— collapsing a genuine zero to None is the same bug with the sign flipped. This
is the same defect class the project has now hit six times.

**(b) `HORIZON_TD = 21` does not tile the monthly rebalance dates.** The comment
says "1-month holding = matches monthly rebalance (no overlap)", but calendar
months are not uniformly 21 sessions, so windows anchored at month starts
sometimes gap and sometimes overlap. Measured on IWM over this window:
buy-and-hold **+4.6%** against **−4.5%** for the compounded 21-session windows —
a 9pp artefact. It hits both models identically and cancels out of IC and of the
quantile spread (both computed WITHIN a date), so the C1 comparison stands, but
`cum_port` / `cum_bench` are not quotable and the report now says so in print.

**What C1 unblocks.** The screener backtest now measures the screener, so any
future change to `scoring.py` can be tested before it ships instead of after.
The immediate follow-ups, in order: finish the insider measurement; chase the
12.9% missing point-in-time share count; and re-run under C5's Sharadar universe,
because a rejected model on a survivorship-biased panel is a *generous* reject —
the real number is worse, not better.

---

---

# ROUND 2 — PRE-REGISTERED THRESHOLDS (C5, O9), written BEFORE either run

Committed first, as before, so neither can be re-derived after seeing a number.

## C5 — the point-in-time universe on REAL data

`core/pit_universe.py` has only ever been verified on a synthetic 30-name mirror
in which 8 names delist mid-window. No real-data run is recorded anywhere. The
number the module exists to produce is `pct_invisible_to_a_live_screener`: of the
names that were genuinely in the universe on a historical date, what share are
dead today and therefore structurally absent from any screener-built universe.

**Data:** the D10 freeze, `data/backtest_freeze_2026-08/bulk/` —
`tickers.csv` (78,881 rows / 48,925 tickers), `sep.csv` (3.2 GB), `daily.csv`
(2.5 GB). Licensed, local, read-only, never committed.

**This is a measurement, not a hypothesis test**, so the pre-registration is about
what the number will be taken to MEAN, which is the part that can otherwise be
chosen afterwards:

* **PASS (the module works on real data)** requires all four:
  1. `PITUniverseBuilder.build()` completes on real data at every tested date;
  2. delisted names are genuinely present in historical universes
     (`delisted_included > 0` on pre-2020 dates) — the module's whole purpose;
  3. universe size is stable and plausible across dates (no date collapsing to
     near-zero, which would indicate a silent join failure rather than a real
     universe);
  4. `AsOfHistory` refuses data after its as-of date **on real data**, not just
     on the synthetic mirror.
* **Interpretation of the bias, fixed in advance.** Let *m* = the MEDIAN of
  `pct_invisible_to_a_live_screener` across the tested dates.
  * **m < 2%** → the bias the module exists to remove is small; prior
    today's-universe results are less compromised than the record claims, and
    that would itself be a correction worth making.
  * **2% <= m <= 10%** → material but bounded.
  * **m > 10%** → prior backtests built on a today's-universe screen are
    artefacts, exactly as the record asserts, and every one of them needs
    re-running before it is quoted again.
* Reported **per period**, never as a single aggregate — the audit asks for the
  per-period figure specifically, and an average over 18 years would hide the
  fact that the bias necessarily grows with distance into the past.
* **Anti-cheat, pre-committed:** the run must NOT filter on
  `TICKERS.scalemarketcap` / `scalerevenue`. Those are max-over-lifetime buckets
  and using them would leak look-ahead into the very universe being validated.
  The module refuses to offer them; the run must not reintroduce them.

## O9 — IV rank as a SELL-timing rule, on index options

`iv_rank` has been rejected three times, always as a filter on a LONG-vol
strategy ("buy calls only when IV rank is low"). That is a different hypothesis
from "sell premium only when IV rank is high, and otherwise do nothing". The VRP
arm's `IV_RANK_MIN >= 0.50` was a floor on an always-on strategy, not a switch,
and its own banding worsens monotonically inside the admitted range
(0.50-0.65: −6.24%, 0.65-0.80: −8.16%, >=0.80: −9.45%) — informative, but measured
inside a strategy whose base rate is negative *because of execution*, so it
cannot separate "high IV rank is bad for short vol" from "high IV rank names have
wider spreads."

O8 removed that confound: on SPY/QQQ/IWM the spread is not the binding
constraint, and O8 established the ungated baseline.

**Design.** Same engine, same 2018-01-01→2025-12-31 primary window, same default
config as O8. Add an entry gate only: **open a new spread only when the index's
own vol index sits in the TOP TERCILE of its trailing 252-session distribution;
otherwise hold cash.** Exits are untouched — this is a sell-*timing* rule, not an
exit rule. IV rank is computed from the vol series alone, strictly from data on
or before the entry date, so it introduces no look-ahead.

**Baseline for comparison:** the O8 ungated numbers already committed above —
SPY excess Sharpe **0.14**, QQQ **−0.05**, IWM **−0.56**.

* **ADOPT (short vol stays open as a research question)** requires, on SPY:
  gated excess Sharpe **>= 0.50** — the same bar O8 used. The gate has to
  *rescue* the strategy, not merely improve it; "less bad" is not a strategy.
* **EFFECT PRESENT (reported separately from the verdict, and decided in
  advance so it cannot be reached for afterwards):** mean P&L per trade in the
  top IV-rank tercile exceeds that in the bottom two terciles, on SPY, over the
  primary window. This is the directional test of the hypothesis itself and is
  independent of the Sharpe bar.
* **CLOSE THE SHORT-VOL QUESTION PERMANENTLY** — the audit's own
  pre-registration — if gated SPY excess Sharpe < 0.50 **and** the effect is not
  present by the definition above.
* If the effect IS present but the Sharpe bar is not cleared, that is **"effect
  real, magnitude insufficient"** and is reported as such rather than rounded to
  either verdict. Honouring the audit's instruction, the question still closes,
  because the audit conditions closure on the *effect* not appearing where
  execution is cheap — and an effect too small to clear the bar on the friendliest
  possible underlying will not survive on single names, which are strictly worse.
* Also reported: **fraction of time invested** (the audit asks for it explicitly)
  and the conditional expectancy by tercile.

---

---

# O9 — IV rank as a SELL-timing rule · REJECTED. **The short-vol question is closed.**

Full numbers: `options_backtest/o9_iv_rank_summary.json`. Threshold committed at
`65b2456`, before the run.

**What was actually tested, and why it was not a re-run.** `iv_rank` had been
rejected three times, always as a filter on a LONG-vol strategy ("buy calls only
when IV rank is low"). That asks whether cheap vol predicts good long-option
outcomes. This asks the opposite question — whether expensive vol predicts good
SHORT-option outcomes — as an on/off switch rather than as a floor on an
always-on strategy. O8 is what made it answerable: on index options execution is
not the binding constraint, so a result here cannot be confounded by "high IV
rank names have wider spreads", which is exactly what made the single-name
banding uninterpretable.

**Design.** Same engine, same 2018-2025 window, same config as O8. Open a spread
only when the index's own vol index sits in the top tercile of its trailing
252-session distribution; otherwise hold cash. **Entries only** — gating exits
would hold losers because vol fell, which is a different and much worse strategy,
and there is a test asserting exits stay ungated.

| | ungated Sharpe | **gated Sharpe** | ann. vol | max DD | trades | time invested |
|---|---|---|---|---|---|---|
| **SPY** | +0.14 | **+0.04** | 15.7% → 8.2% | −23.2% → −14.5% | 1,905 → 538 | **27.2%** |
| QQQ | −0.05 | **−0.28** | 16.0% → 9.1% | −33.3% → −26.2% | 1,907 → 542 | 27.9% |
| IWM | −0.56 | **+0.12** | 13.8% → 6.6% | −46.8% → −11.8% | 1,892 → 491 | 24.8% |

**ADOPT required SPY gated excess Sharpe >= 0.50. It is 0.04 — and it is WORSE
than ungated.** The gate roughly halves volatility on every underlying, so it is
a genuine risk reducer; on the primary underlying it simply cuts return by more
than it cuts risk (annualised return 4.68% → 2.86%, against a 2.54% risk-free).

## The decisive result is not the Sharpe — the sign flips across underlyings

Ungated mean P&L per trade, by IV-rank tercile (terciles cut on the *observed*
rank distribution, because IV rank is not uniform on [0,1]):

| | bottom | middle | top | shape |
|---|---|---|---|---|
| **SPY** | **$56.73** | $0.16 | $47.34 | non-monotone; **cheapest tercile is best** |
| **QQQ** | **$68.76** | −$3.83 | −$8.46 | monotone **decreasing** — top is worst |
| **IWM** | −$35.28 | −$17.69 | **$29.98** | monotone **increasing** — top is best |

My pre-registered "effect present" test — top tercile above the bottom two, on
SPY — **fires TRUE** ($47.34 vs $28.50). I am reporting that because it was
pre-registered, but it does not mean what it was written to test: it fires only
because the middle tercile is ≈$0, and on SPY the **cheapest** vol tercile is the
best of the three, which is the opposite of the hypothesis. On QQQ the ordering
is cleanly monotone in the *wrong* direction.

A rule whose sign flips between SPY, QQQ and IWM over the same eight years is not
a rule. One positive out of three underlyings is what chance looks like. IWM's
improvement (−0.56 → +0.12) is the single result that superficially supports the
idea, and it still does not clear the bar.

**Verdict: REJECTED.** Per the audit's own pre-registration — *"if the effect
does not appear on index options where the spread is small, close the question
permanently"* — **the short-vol question is closed.** Not "parked": closed. The
friendliest possible execution environment, the two prior rejections, O8's
cost decomposition and now this all point the same way, and there is no version
of this that survives on single names, which are strictly worse on every axis
that matters.

**What it unblocks.** Nothing further should be spent on short vol —
re-parameterisation, different deltas, different DTEs, IV-rank variants. If it is
ever reopened it needs a *new mechanism*, not a new parameter, and a fresh
pre-registration that says so.

**Two construction notes worth keeping.**
* `iv_rank_series` computes the **percentile** form (fraction of the trailing
  window at or below today), not the `(IV − low)/(high − low)` range form. The
  range form is hostage to two extreme observations, so one 2020-03 print pins it
  near zero for the following year — switching the rule OFF precisely when
  premium is richest. That choice would have changed the answer.
* Days whose trailing window is not yet full get **no signal and do not trade**.
  Consequently 243 of SPY's 1,905 ungated trades (12.8%) carry no rank and are
  excluded from the tercile table, which is why the tercile P&L does not sum to
  the strategy total. The counts are reported (`trades_without_a_rank`) rather
  than left for a reader to trip over.

13 tests (`options_backtest/test_iv_rank.py`), the important one asserting that
every rank on or before day K is unchanged when vol after day K is replaced with
a huge spike — a sell-timing rule that peeks one day forward would look excellent
and be worthless, and nothing in the equity curve would say so.

---

---

# C5 — the PIT universe on real data · PASSED, after fixing a bug that made it return NOTHING

Per-period numbers: `data/c5_survivorship.json` (gitignored — derived from
licensed data). Threshold committed at `65b2456`, before the run.

## The first result was an empty universe on all 27 dates

`core/pit_universe.py` had only ever been exercised against a synthetic 30-name
mirror. Pointed at the D10 freeze it returned **universe size ZERO on every
annual date from 2000 to 2026**.

**Cause.** Sharadar's `DAILY.marketcap` is denominated in **millions of USD**.
`PITUniverseConfig.min_market_cap` is written in **dollars** (`2_000_000_000`).
So AAPL on 2015-06-30 presented as `722571.4` against a `2e9` floor and failed
the cap gate — as did every company that has ever listed. 5,945 names were listed
that day; the universe was empty.

Cross-checked before touching anything: `722,571.4 × 1e6 = $722.57B`, which
matches this project's own recorded *"AAPL 2015Q2 $722.6B verified"* from the
same table. The main tree already knew the units; this module did not.

**Why the test suite certified it anyway — this is the actual lesson.** The
synthetic fixture in `tests/test_sharadar.py` wrote market caps in **dollars**
(`GOOD = 5e9`, `TINY = 1e8`) directly into the `daily` table. The mirror spoke
dollars; the feed speaks millions. So the suite was green on a module that
**cannot** return a non-empty universe on real data.

> A synthetic fixture cannot disagree with you about what the real feed means.
> Its author picks the units, and naturally picks the ones the code expects.

That is precisely why "verified end to end on a synthetic mirror" is not
verification, and it is the whole reason C5 was worth doing. The audit called C5
"Effort: S" — it was, and it found a defect that silently disabled the module the
entire survivorship-bias programme depends on.

**Fixed** in `SharadarStore.marketcap_on` (normalise once, return dollars, named
constant `MARKETCAP_UNITS_PER_USD`) and in the fixture (specs stay in dollars and
are converted on insert, in the same direction the real loader converts).

## The C5 deliverable — invisible-name count PER PERIOD

Share of each historical universe that is **dead today**, and therefore
structurally absent from any universe a live screener could build:

| as-of | universe | delisted since | **invisible** | examples |
|---|---|---|---|---|
| 2000-06-30 | 588 | 339 | **57.7%** | WCOEQ (WorldCom), LU1 (Lucent), JAVA1 (Sun), EMC1, DELL1 |
| 2003-06-30 | 487 | 221 | 45.4% | WYE, WB1, BLS, TFCF |
| 2007-06-30 | 872 | 384 | 44.0% | MER (Merrill), WB1, DNA1, TWX |
| 2010-06-30 | 626 | 217 | 34.7% | TWX, DD1, DTV1, ESRX |
| 2013-06-30 | 819 | 263 | 32.1% | TFCF, MON2, ESRX, EMC1 |
| 2016-06-30 | 881 | 245 | 27.8% | AGN, RAI, CELG, TWX |
| 2019-06-30 | 937 | 164 | 17.5% | VMW, CELG, AGN, RTN |
| 2022-06-30 | 963 | 121 | 12.6% | ATVI, PXD, VMW, HES |
| 2024-06-30 | 982 | 62 | 6.3% | HES, DFS, ANSS, CTRA |
| 2026-06-30 | 1,279 | 8 | 0.6% | GTLS, BLD, NUVL, JHG |

**Median 32.1% across 27 periods** (min 0.6%, max 57.7%), declining monotonically
with recency exactly as it must.

**Pre-registered band: `m > 10%` → prior today's-universe backtests are
ARTEFACTS.** The median is 32.1%, three times the threshold. This is not a
marginal call.

Put plainly: a backtest of 2013 built from today's screener is missing **roughly
a third of the companies that actually existed**, and they are not a random
third — they are the ones that were acquired or went to zero. The examples are
the tell: WorldCom in the 2000 universe is precisely the name a
survivor-built universe deletes.

**All four pre-registered PASS conditions met:**
1. `build()` completes on every tested date — yes, after the units fix.
2. Delisted names genuinely present in historical universes — 144 to 384 per
   pre-2020 date.
3. Universe sizes plausible and stable — 463 to 1,279, no date collapsing.
4. `AsOfHistory` refuses post-as-of bars **on real data** — 42 bars returned for
   XOM around 2013-06-30, **0** after the as-of. PASS.
5. Anti-cheat: `scalemarketcap`/`scalerevenue` are absent from the schema
   entirely, so the look-ahead filter is structurally impossible, not merely
   discouraged. PASS.

## What this does NOT cover, stated plainly

The audit asks to run `scripts/run_sharadar_backtest.py`. **I ran the point-in-time
universe and the survivorship report — the number the audit actually asks for —
but not the full bot backtest.** The mirror is date-*windowed* (60 days around
each of 27 as-of dates) rather than continuous, because a continuous mirror is
~86M rows and tens of GB. The survivorship report needs only "price then, cap
then, volume then"; a strategy backtest needs unbroken series for signals.

To run the bots on real data, rebuild with a continuous date range over the
window of interest and then run the existing script:

```
python scripts/build_freeze_mirror.py --freeze <freeze>/bulk --db <db> \
    --dates <every trading date in range>      # or widen --window-days
python scripts/run_sharadar_backtest.py --bots momentum reversion --years 5
```

**What it unblocks.** Every prior backtest built on a today's-universe screen now
has a measured bias figure attached to it, per period, instead of an assertion.
The momentum result the record flags as "close to fatal" is confirmed as
artefact-scale: a 2021-2024 window carries 12-17% invisible names, and the
further back a result reaches the worse it gets.

**Housekeeping:** the mirror is `data/c5_pit_mirror.db` (~1.5 GB, gitignored,
derived from licensed data, regenerable in ~35 min). Delete it freely.

---

*Note: `HANDOFF_STATUS.md` has deliberately NOT been overwritten. Several agents
are working parallel lanes against this repo and that file is shared project
state; overwriting it from one lane would clobber the others. This file is this
lane's full report.*
