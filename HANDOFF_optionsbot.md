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

---

<!-- ledger:ignore -->
<!-- This section WRITES ABOUT the ledger and names item ids without being
     evidence about them. build_ledger.py skips everything between these
     markers, so the report cannot feed its own counts back in on refresh. -->

# OUT-OF-BAND — `VALQUO_LEDGER.md`, so nobody reconstructs project state from git again

**Status: infrastructure, not a measurement.** No audit item was executed here and no
threshold was pre-registered, because nothing was run. Two new files only:
`VALQUO_LEDGER.md` and `scripts/build_ledger.py`. Nothing existing was modified —
not `CLAUDE.md`, not `RUN_RULES.md`, not any other lane's `HANDOFF_*.md`.

## Where we stand — 134 items, one table

| series | DONE | IN PROGRESS | BLOCKED | OPEN | total |
|---|---|---|---|---|---|
| B | 23 | 1 | 1 | 1 | 26 |
| R | 6 | 0 | 4 | 0 | 10 |
| X | 6 | 0 | 0 | 2 | 8 |
| S | 1 | 0 | 0 | 27 | 28 |
| O | 5 | 0 | 0 | 21 | 26 |
| U | 1 | 0 | 0 | 7 | 8 |
| C | 6 | 0 | 1 | 0 | 7 |
| P | 2 | 0 | 0 | 3 | 5 |
| D | 2 | 0 | 0 | 8 | 10 |
| M | 2 | 0 | 0 | 4 | 6 |
| **all** | **54** | **1** | **6** | **73** | **134** |

**78 of the 134 rows are hand-verified** (`src=human`) — I read the write-up before
setting the status. The other 56 are mechanical proposals marked `src=auto` and should
be treated as leads, not facts. Every `DONE` row carries a checkable sha except `P5`,
which is flagged in its own note as the weakest `DONE` in the file.

The two prior counts were 38/134 and 68/134. Neither is right. **54 is the number**, and
unlike the other two it is per-item and checkable in one step.

## The four traps that produced the wrong counts

These are now encoded in `build_ledger.py` and written into the ledger's header:

1. **A forward reference is not a completion.** "feeds U1", "needed for S12", and
   critically `## Task 3 — schema conformance (supports D1, ...)` — a forward reference
   *inside a heading*, which any header-matching rule scores as strong evidence. This is
   the specific error behind the 68.
2. **`P1`–`P5` collide with the project's own PHASE labels.** CLAUDE.md's
   "~~P3 — SF3 smart-money conviction~~ **DONE (P4 commit)**" is phase P4. **Audit item
   P4 is open** and explicitly "out of band for this audit, flagged in" — the opposite.
3. **`M2` is a different document's item.** HANDOFF_STATUS.md's "The audit's M2
   (SanDisk/WDC) does NOT reproduce" is `CODE_AUDIT.md`'s M2. The external audit's M2 is
   "clustered inference default" and **has never been touched**. It was reading as
   IN PROGRESS until this was caught.
4. **`D1`–`D10` collide with DECILE labels** — "long-short (D1-D10)", "D1 22.8% → D10
   10.7%" — which this project writes constantly.

## Where sources disagree — these are findings, not bookkeeping

1. **B26 — the write-up and the commit log disagree on the outcome.**
   `HANDOFF_edge_audit.md` says "**Verdict: all FIXED**"; commit `2ded1f3` is
   "**RETRACTION: B26 did not flip the insider theme — the backtest is not
   reproducible**". The fix landed; the *effect* claimed for it was retracted. Recorded
   `DONE` with `DISPUTED` in the note. **Someone who owns the edge lane should confirm
   which claim stands.**
2. **M1 — `ADOPTED` in its write-up, but not finished.** `AGENTS.md` lists "**M1's
   re-run**" among the r1 lane's open items. Recorded `DONE` (the log and the N=8→84
   recount shipped) with the outstanding re-run named in the note.
3. **D7 — asserted, never written up.** `VALQUO_ACTION_PLAN.md` states "WRDS is the #1
   lever" → **dead end (D7)** as settled fact. There is **no write-up and no commit for
   D7 anywhere in the corpus.** Recorded `OPEN`/`DISPUTED`. Either the conclusion is real
   and unrecorded, or it is an assumption that has been load-bearing for a while — and
   `U2` is described as replacing it, so it matters.
4. **B13 — "PARTIALLY FIXED" was recorded as `IN PROGRESS`, not `DONE`.** The categorical
   filters bind; `MIN_AVG_DOLLAR_VOLUME` still cannot. It is the only `IN PROGRESS` row
   in the file and it is a judgement call — flagging it so it can be overruled cheaply.
5. **C6 (mine) — `BLOCKED`, not `DONE`.** Its own verdict line reads "the three fixes are
   **ADOPTED-in-repo and still UNDEPLOYED**". Recording that as `DONE` would have hidden
   a live blocker.

**A meta-finding worth more than any single row: a mechanical verdict scrape is
unreliable and must not be trusted.** The extractor proposed `INCONCLUSIVE` for R2 (real
verdict **REJECTED**), `NULL` for R9 and R10 (both **ADOPTED**), `ADOPTED` for O8 (real:
**INCONCLUSIVE** on SPY, **REJECTED** on QQQ/IWM) and `ADOPTED` for C1 (real:
**REJECTED**). Cause: it matched verdict words appearing in the *pre-registration* text
that precedes the result. This is why the ledger separates `human` from `auto` rows
rather than presenting one number.

## Left OPEN deliberately, for want of evidence

An item wrongly marked done stops work happening; one wrongly marked open costs a
re-check. Where it was ambiguous I left it `OPEN` and put the reason in the note.

- **37 with zero substantive mentions anywhere in the corpus:** S6 S8 S9 S11 S12 S13 S15
  S16 S18 S19 S20 S21 S22 S24 S25 S28 O10 O11 O14 O16 O17 O18 O19 O21 O22 O23 O24 O25 O26
  U3 U8 D2 D4 D6 D8 D9 M4
- **14 with prose mentions only** (named, never written up): S1 S2 S3 S4 S5 S7 S17 O1 O6
  O13 P3 D5 M3 M6
- **5 mentioned only as somebody else's dependency:** S10 S14 S23 S27 P2

The remaining 17 open rows were set by hand and carry a specific reason instead.

The S series is the honest headline: **27 of 28 open, and 16 of those have never been
substantively mentioned once.** It is the largest untouched block in the audit.

**"Substantive" is doing real work in that sentence, and it is a finding of its own.**
A line that lists many ids — `| 8+ | O1, S20, S21, X1, S2, S19, X8, ... — descending
value |` in `VALQUO_ACTION_PLAN.md`, or a scope list like "**Scope run:** B2, B4, B5, B6,
B7, B11, B13, ..." — is a **roll-call, not evidence about any item on it**. The builder
ignores lines carrying 7+ ids for exactly this reason. Without that rule S19, S20 and S21
look "mentioned" when the only thing that ever happened to them is being listed in a plan.
It also stops the ledger becoming self-referential: publishing "these 36 items are never
mentioned" would otherwise become a mention of all 36, on the next refresh.

There was a second, sharper version of the same loop, and it is fixed rather than
documented: **this report is itself part of the scanned corpus.** Naming S19/S20/S21 in
the paragraph above gave them prose mentions, which moved them between categories on the
next refresh — the counts chased my own prose. This whole section is now wrapped in
`<!-- ledger:ignore -->` markers that `build_ledger.py` honours, so writing *about* the
ledger can no longer feed *into* it. Any document can use the same markers.

**Six items are `BLOCKED` rather than open, with the blocker named:** R4, R5, R6, R8 and
B8 all sit in `valuation/edge/**`, which the pipeline-builder lane holds (per
`AGENTS.md`); C6 needs Don to `scp` `quant_bots/data/*.py` off the box.

**Newly unblocked and nobody appears to have noticed:** O3, O4, O5, O7 and U7 were all
"held until R1 returns". **R1 has returned.** O12 was blocked on B3, which is fixed.

## Refresh — one command

    python scripts/build_ledger.py            # proposal + counts by series/status, writes nothing
    python scripts/build_ledger.py --write    # refresh src=auto rows ONLY; never touches src=human
    python scripts/build_ledger.py --evidence S12   # every occurrence, classified, + the commits

`--write` is safe to run repeatedly: it is idempotent, and on a hand-verified row it
prints a **DISAGREEMENT** line and leaves the row alone rather than clobbering it.

## Two things I did NOT do, deliberately

1. **I did not edit `RUN_RULES.md` or `CLAUDE.md`** — the prompt reserved that. Proposed
   wording for whichever lane owns `RUN_RULES.md`, to sit beside the existing "code
   without a handoff entry is not finished work" rule:

   > **A landed audit item with no `VALQUO_LEDGER.md` row is not finished work.** Update
   > your rows as part of your handoff. The ledger is the answer to "where do we stand";
   > if it cannot answer, fixing the ledger is the task — never another archaeology dig.
   > Rows are append-and-amend: a status that changes keeps its history in the note.

2. **I did not add a test pinning the four collision rules**, because the prompt scoped
   this to two new files. It is the obvious follow-up and it is cheap — this project has
   been bitten four times by guards going silently inert, and these rules are exactly
   that kind of guard.

## One infrastructure finding, unrelated but load-bearing

**`valquo_audit_items.json`, `VALQUO_EDGE_AUDIT.md`, `VALQUO_ACTION_PLAN.md` and
`AGENTS.md` are NOT in git.** They are not gitignored — they were simply never added.
They exist only in Don's shared checkout at `C:\Users\donni\Downloads\valuation-tool\`.

Consequences: the audit's own source of truth cannot be recovered if that folder is lost,
it is invisible to every worktree (`build_ledger.py` has to reach up three levels to find
it), and no agent working from a clean clone can see the item list at all. **Someone
should `git add` those four files.** I did not, because the prompt restricted me to
creating two new files and these are pre-existing documents I do not own.

*`HANDOFF_STATUS.md` again deliberately NOT overwritten — shared state, parallel lanes.*

<!-- /ledger:ignore -->

---

# AUDIT M3 — DONE 2026-08-06, `tests/test_guards.py`

<!-- The heading above is deliberately OUTSIDE the ignore block: it is this lane's completion
     evidence for M3 and `build_ledger.py` must see it. Everything below is inside, because the
     write-up CITES R9, R10, O15, B4, B22 and M6 as context — those are mentions, not
     completions, and feeding them to the scanner is precisely the forward-reference error that
     produced the bad 68/134 count. -->
<!-- ledger:ignore -->

**Done 2026-08-06.** Deliverable: `tests/test_guards.py`, 36 tests, **35 pass and 1 XFAIL**.
No production file was modified. `python tests/test_guards.py` exits 0.

M3 exists because this project has been bitten at least six times by one shape: a check exists,
the run completes, and the check was not looking. Every one of those had a guard, a test suite or
an audit nearby. **What none of them had was a test that fed the guard a known-bad input and
asserted it complained.** A guard that has never fired is indistinguishable from a guard that
cannot fire, and this project has shipped both.

Two rules the fixtures follow: **use the real failure where one is known** (the KSPI 14.0x fair
value, the `-1` OI sentinel, the R9 4.517 lost at the schema boundary, the NXPI-2017 symbol-year
that vanished into its own backup), and **assert the refusal direction too** — every fixture set
carries a clean input that must NOT trip the guard, because a guard that fires on everything is
switched off faster than one that fires on nothing.

## THE HEADLINE: the guards are in better shape than the record implies, with two exceptions

**29 of the 30 testable guards fire on the bug they exist to catch.** The exceptions:

1. **`oi_coverage_audit.year_files` cannot see a symbol-year that vanished** — the known-bad
   fixture is NXPI-2017 and it is not caught. Shipped as XFAIL, routed below.
2. **There is no field-level schema guard at all.** `missing_result_blocks` guards BLOCK
   absence; the R9 loss (`top_decile_alpha_tstat` = 4.517 computed correctly and written as
   `None`) was FIELD-level, and that hole is still open. Not a guard that fails — a guard that
   was never written.

Everything else complained when it was shown the bug, including several I expected to fail.

## Guard census

`fires?` means: fed a fixture reproducing the failure it exists to catch, does it complain —
and does it stay quiet on a clean input. **PINNED (M3)** = had no behavioural test before this
item. **pre-M3** = already had one; re-checked here and listed so the census is complete.

### Tier 1 — between a wrong number and a USER

| guard | file:line | what it catches | fixture | fires? | lane |
|---|---|---|---|---|---|
| `publication_guard` / `publication.decide` | `engine/pipeline.py:36`, `engine/publication.py:83` | a fair value more than 5x price | **real KSPI $1,289.60 vs $92.19 = 14.0x** | YES — **PINNED (M3)**, had ZERO tests | app fixer |
| — its currency leg | `engine/publication.py:66` | statements in KZT, price in USD, no usable rate | fx unresolved at a 1.19x ratio (inside the band) | YES — **PINNED (M3)** | app fixer |
| — the band boundary | `engine/publication.py:36` | an off-by-one silently re-valuing every borderline name | exactly 5.0x publishes; 5.0x + 0.01 refuses | YES — **PINNED (M3)** | app fixer |
| `fairvalue._mature_value` band | `screener/fairvalue.py:186` | a levered EV re-rating implying 12.4x per share | **CHTR's 4.68x leverage at the 3x re-rate cap** | YES — **PINNED (M3)** | app fixer |
| `fairvalue._pos_yield` | `screener/fairvalue.py:92` | pricing off a negative earnings yield | loss-maker at −0.08 vs peers at +0.05 | YES — **PINNED (M3)** | app fixer |
| `record_refusal` + `estimate_fair_values` | `engine/publication.py:120`, `screener/fairvalue.py:270` | a refusal erased by a peer substitute — how KSPI, STLA, CHTR reached the public hot list | a recorded refusal against a full peer set | YES — **PINNED (M3)** end-to-end | app fixer |
| `withhold_implausible_fair_values` | `web/withhold.py:168` | any row past the band, **including NaN** | NaN driven through all three steps | YES — **PINNED (M3)**; see the finding below | app fixer |
| `withhold_derived_figures` | `web/withhold.py:261` | every figure derived from a withheld value | the real KSPI payload | YES — pre-M3 (`test_withhold.py`, 28 tests), re-checked | app fixer |
| `scoring.py` >5x cap | `engine/scoring.py:228` | the cap that could not fire once `base_fv = None` | pre-M3 (`test_engine.py:499`) | YES — pre-M3 | app fixer |

### Tier 2 — between a wrong number and a RESEARCH VERDICT

| guard | file:line | what it catches | fixture | fires? | lane |
|---|---|---|---|---|---|
| `missing_result_blocks` | `edge/fundamental_panel.py:4199` | a validation block that never ran — R10's `benchmarks` | absent / `{}` / `None`, all three | YES — **PINNED (M3)**, had ZERO tests | pipeline builder |
| `build_payload` errors scan | `edge/results_file.py:123` | a block that raised, reading as "ran and found nothing" | `status: "error: boom"` | YES — **PINNED (M3)** | pipeline builder |
| the R9/R10 fields | `edge/results_file.py:217-228` | the exact two the writer dropped | `top_decile_alpha_tstat` 4.517, `benchmarks` | YES — **PINNED (M3)** | pipeline builder |
| **field-level schema** | `edge/results_file.py:74` | a NEW metric added to a computation | a field nobody whitelisted | **NO GUARD EXISTS** — characterised, see BUGS FOUND | pipeline builder |
| `signal_coverage` | `edge/fundamental_panel.py:3781` | a wired factor non-null in 0 rows | all-null `z_roe`, named **with its theme** | YES — **PINNED (M3)** for the theme attribution; coverage itself pre-M3 | pipeline builder |
| `sanity_check` (panel) | `edge/fundamental_panel.py:3614` | the currency bug — present but wrong | a 1000x fx divisor, the SK Telecom magnitude | YES — pre-M3 (`test_edge.py:1052`) | pipeline builder |
| `ev_freshness` | `edge/fundamental_panel.py:3830` | a silent revert of point-in-time EV | pre-M3 (`test_ev_multiples.py:394`) | YES — pre-M3 | pipeline builder |
| `composite` NaN handling | `edge/fundamental_panel.py:1549` | a name with no themes ranking mid-pack | pre-M3 (`test_edge.py:4453`) | YES — pre-M3 | pipeline builder |
| `options_vrp.coverage_block` | `edge/options_vrp.py:777` | an options input absent on every trade | `iv_rank = None` on all rows, and on 49 of 50 | YES — **PINNED (M3)**, had ZERO tests | options bot |
| `options_vrp.sanity_block` | `edge/options_vrp.py:801` | arithmetically impossible trades | −150% loss, credit > width, 0.80 delta, **400 DTE**, one-exit-reason | YES — partly pre-M3 (`test_edge.py:2416`); M3 adds the DTE window and exit dominance | options bot |
| `options_autopsy.feature_coverage` | `edge/options_autopsy.py:530` | a feature present but non-numeric | `"n/a"` strings on every row | YES — **PINNED (M3)** | options bot |
| `blackscholes.validate_against_vendor` | `edge/blackscholes.py:252` | a hand-rolled pricer that is quietly wrong | every delta off by −0.20 | YES — **PINNED (M3)**, but **never called anywhere** | greeks lane |
| `options_stats.clustering_measurable` | `edge/options_stats.py:197` | a design effect quoted without its null | pre-M3 | YES — pre-M3 | options bot |

### Tier 3 — between a wrong number and the DATA ON DISK

| guard | file:line | what it catches | fixture | fires? | lane |
|---|---|---|---|---|---|
| `oi_coverage` | `edge/theta_bulk.py:260` | `-1` read as a quantity | pre-M3 (`test_edge.py:4557`) | YES — pre-M3 | options bot |
| `.oi_degraded` sidecar (writer) | `edge/theta_bulk.py:674-695` | a faulted OI call cached as a complete year | an all-`-1` frame through a stubbed `_fetch_year`, then a clean re-mine | YES both ways — pre-M3, re-checked | options bot |
| deepening must not lose rows (O15) | `edge/theta_bulk.py:700-705` | a "deeper" pull thinner than the cached one | 30 rows against a cached 160; then a genuine 400-row superset | YES — pre-M3, M3 adds the depth-stamp assertion | options bot |
| `depth_report` | `edge/theta_bulk.py:285` | a partial deepening reading as uniform | DEEP / MIXED / LEGACY (no `.dte` sidecar) | YES — pre-M3, M3 adds the legacy and empty-root cases | options bot |
| `alias_overlap_conflicts` | `edge/theta_bulk.py:334` | `WBD -> T`: an "alias" that is a live company | overlapping cached years, and DISCA's clean handover | YES — pre-M3, re-checked | options bot |
| `oi_coverage_audit.scan_one` | `oi_coverage_audit.py:40` | `-1` vs a genuine 0; unreadable / empty / no-column | all four shapes | YES — **PINNED (M3)**, had ZERO tests | options bot |
| **`oi_coverage_audit.year_files`** | `oi_coverage_audit.py:57` | a symbol-year that vanished from the cache | **NXPI-2017 as a `.bak_oi` orphan** | **NO — XFAIL** | options bot |
| `oi_remine` orphan sweep | `oi_remine.py:96-121` | the NXPI-2017 loss (144,300 rows) | an orphan on disk, network stubbed to a keyless client | YES — **PINNED (M3) behaviourally**; the prior test asserted on SOURCE TEXT | options bot |
| `oi_remine` never-destroy | `oi_remine.py:168-198` | a stale backup restored over a healthy frame | `.bak_oi` beside a live `.pkl` | YES — **PINNED (M3)** | options bot |
| `oi_remine` no-key refusal | `oi_remine.py:124-126` | marking every span permanently `.oi_nosource` | a keyless client with a span below the floor | YES — **PINNED (M3)** | options bot |

### Could NOT be fixture-tested — recorded, not skipped

| guard | why not | lane |
|---|---|---|
| `check_lanes.py` | **NOT IN GIT.** `git ls-files` does not know it; it is not gitignored either, just never added. No worktree and no clean clone can run it, so it cannot be tested from the repo. Same class as the four untracked audit documents. | audit tooling — needs an owner |
| `theta_bulk._fetch_span` retry/backoff | Needs a live ThetaData subscription; the policy is only observable against a feed that is actually faulting. | options bot |
| `options_greeks.repair_coverage` | Needs the mined cache (~18GB) plus a live feed to re-pull what it repairs. | greeks lane |
| `build_fundamental_panel` end-to-end | Needs the licensed Sharadar exports in `data/backtest`. The guards INSIDE it — `signal_coverage`, `sanity_check`, `ev_freshness` — are each pinned separately above. | pipeline builder |

The list is pinned by `test_the_untestable_list_is_specific_rather_than_a_shrug`, which requires
every entry to name a real blocker — so the row cannot quietly become the place to put guards
nobody wanted to write.

## BUGS FOUND

**None of these were repaired here.** The fix belongs to the lane that owns the file; repairing
it in this session would mean the test and the fix land together with nobody having seen the
test fail.

### 1. `oi_coverage_audit.year_files` is blind to a symbol-year that vanished — XFAIL

`oi_coverage_audit.py:57`. **Owning lane: options bot (this one).** The enumeration is
`fn.endswith(".pkl")`, so a symbol-year that exists only as a `.bak_oi` orphan is not scanned,
not counted, and not reported. Its absence reads as a **repair**: the span drops out of
`below_floor` and the before/after diff calls it fixed.

That is not hypothetical — it is the recorded NXPI-2017 loss (144,300 rows, 6.8MB), which
appeared in a coverage diff as one of three "fixed" spans after a shard was stopped mid-re-pull.

`oi_remine` sweeps orphans back at the START of its own run, which **mitigates but does not
close it**: an audit run while a shard is stopped still cannot see the gap, and the sweep only
runs when someone runs the re-miner. **This wants a decision, not a patch** — either the audit
counts orphans, or it records the cache's file inventory so a shrinking one is loud. I did not
pick, because either choice changes what `OI_COVERAGE.json` means and that file is committed and
quoted.

Test: `test_the_oi_audit_can_see_a_symbol_year_that_vanished_into_its_backup`, registered
`@known_failure`. It goes green the day the guard is fixed, and the runner prints `XPASS` telling
whoever fixed it to delete the marker.

### 2. Nothing guards the schema boundary at FIELD level

`edge/results_file.py:74`. **Owning lane: pipeline builder.** `build_payload` whitelists every
key it writes. The R9 loss was exactly this: `quantile_backtest` computed
`top_decile_alpha_tstat = 4.517421601141459` correctly and the canonical file recorded `None`
beside it. Nothing raised. `benchmarks` was added to `RESULT_BLOCKS` afterwards, which closes
that one BLOCK — it does not close the class.

Measured today: `build_payload({"construction": {"a_brand_new_metric": 1.23}})` returns a
`construction` block with no such key and no complaint. **Adding a metric to a computation does
not add it to the canonical file, and the canonical file is what every other agent reads.**

Pinned as a characterisation test (`test_the_schema_boundary_still_drops_a_metric_nobody_
whitelisted`) whose assertion message says "GOOD NEWS ... delete this" — so it fails loudly the
day someone closes the hole, rather than sitting as a silent assumption.

### 3. `validate_against_vendor` has no caller anywhere in the tree

`edge/blackscholes.py:252`. **Owning lane: greeks lane.** It exists "because a hand-rolled
pricer that is subtly wrong would corrupt every signal downstream while every run completed
normally". It works — M3 pins it against a uniformly-wrong delta — and **it is never invoked**:
`grep -rn validate_against_vendor` finds the definition and its own docstring, nothing else. The
purest form of the failure M3 was written for.

Second-order: a no-overlap comparison returns `{"n": 0}` with **no agreement fields at all**, so
a future caller writing `.get("delta_agree_pct", 1.0)` would read a total miss as a perfect
score. Both are pinned; the wiring decision is the greeks lane's.

### 4. A NaN fair value is invisible to two of the three guards in its own chain

**Not a bug today — a one-edit-away hazard, recorded so it stays that way.** Measured:

* `publication.decide(NaN, price)` refuses **with an empty reason**, so `record_refusal` is
  never called and the row is never marked;
* `estimate_fair_values` reads `fair_value is not None` as "a DCF exists" and tags the row
  `dcf`, leaving the NaN in place;
* `withhold_implausible_fair_values` catches it — **only because it is written to CONTINUE when
  the row is provably fine, rather than to WITHHOLD when it is provably bad.** Every NaN
  comparison is False in both directions, so the fail-open form (`if ratio > band: withhold`)
  passes it straight through.

That inversion is the entire defence and it looks like a stylistic choice. Now pinned by
`test_the_public_row_guard_is_fail_closed_against_a_nan_fair_value`.

### 5. The pre-M3 test for the `oi_remine` orphan sweep asserted on SOURCE TEXT

`tests/test_edge.py:4631`. It reads `oi_remine.py` and checks that `".bak_oi"` and
`"recovered orphaned backup"` appear in it, in the right order. That is a reasonable static
check of ordering and it caught a real design requirement — but **it passes just as happily if
the sweep is commented out**, since the strings survive in a comment. M3 replaces it with a
behavioural test that puts an orphan on disk, runs `oi_remine.main()` against a temporary cache
with the network stubbed to a keyless client, and asserts the frame comes back with its rows.
The old test is left in place (it pins the ordering); no lane action needed.

## How to run it

    python tests/test_guards.py          # exits 0; XFAIL does not turn the suite red

It is picked up automatically by the CI gate (`.github/workflows/land-agent-branch.yml` runs
every `tests/test_*.py`).

**On the XFAIL mechanism.** This project runs tests as plain scripts, so there is no pytest and
no `xfail`. `@known_failure(reason, lane)` is this suite's version: a marked test that fails
prints `XFAIL` with the reason and the owning lane and does **not** turn the suite red — the
repair is not this lane's, and landing the test with the fix would mean nobody ever saw it fail.
A marked test that PASSES prints `XPASS` telling you to delete the marker, and also does not
fail the run, so another lane fixing its own bug never breaks this gate.

**And that mechanism is itself pinned**, because by this item's own argument an untested
`known_failure` is indistinguishable from a broken one — if it silently swallowed everything,
the single real finding in this file would read as a pass and nobody would chase it.
`test_this_files_own_xfail_mechanism_is_not_itself_inert` exercises all four routings against
**the same `_classify` the runner calls** (not a copy of the rule, which is the mistake this
file exists to catch), requires every marker to name a live test, a reason over 80 characters
and an owning lane, and pins that a CRASH is never an XFAIL — a marked test throwing a
`TypeError` has rotted rather than found something, and filing that under "expected" is how a
marker outlives its bug. The XPASS path was also driven end-to-end with a deliberately stale
marker: it prints and the suite stays green.

## A ledger note for whoever owns M6

`VALQUO_LEDGER.md` records **M6 (Results-file schema assertion) as OPEN**. M3's census says that
is **half wrong and half right**, which is why I did not change someone else's row:

* the BLOCK-level half **exists and works** — `missing_result_blocks` is real, is called at
  `fundamental_panel.py:4166`, and now has a behavioural test it did not have before;
* the FIELD-level half **does not exist at all**, and that is the half the R9 loss actually came
  through (BUGS FOUND item 2).

So M6 is closer to IN PROGRESS than OPEN, and its remaining scope is field-level only. The
owning lane should set the status; per the ledger's own rule I report the disagreement rather
than overwrite the row.

## What I deliberately did not do

* **No production file was touched.** `git diff --stat` for this item is one new file.
* **I did not fix the two real defects** (items 1 and 2 above), per the prompt: a guard that
  fails its known-bad fixture is the most valuable output of this task, and repairing it here
  would land the test and the fix together with nobody having seen the test fail.
* **I did not add the missing field-level schema guard.** It belongs in `results_file.py`, which
  is the pipeline builder's, and it is a design choice (assert a known key set, or pass unknown
  numerics through) rather than a patch.

<!-- /ledger:ignore -->


---

# C6 CLOSED — the Oracle box is decommissioned, and the blocker it named was never real (2026-08-07)

**Status: DONE.** Ledger row `C6` moved `BLOCKED` → `DONE`, verdict `ADOPTED`, dated 2026-08-07.

## The one-sentence version

The three FIXES.md fixes could not be deployed because `options/data/*.py` was untracked; the
record said those sources existed "only on the Oracle box"; **they were in
`options-bot/handoff/quant_bots.zip`, tracked in this repository the entire time**, and they came
back byte-identical without anyone touching the box — which is fortunate, because the box is gone.

## What the record said, and what was actually true

The earlier C6 write-up (above, "BLOCKER — needs Don, one command") was right about the mechanism
and wrong about the remedy. Its mechanism still stands and is worth keeping: the repo-root
`.gitignore` carried a bare `data/`, a pattern whose only slash is the trailing one matches at every
depth, so it excluded the options bot's **source** package along with the licensed Sharadar
exports it was written for. That is why a clean clone could not run the options suite, and why
`deploy.sh` aborted before restarting anything.

> **That root rule changed on 2026-08-07, while this task was in flight, and the change is
> independent corroboration.** Another lane anchored it to `/data/` because the same unanchored
> pattern was ALSO silently swallowing `valuation/data/` — application source in the main product,
> where a new `valuation/data/beta.py` was unaddable and would have shipped as a runtime
> `ModuleNotFoundError`. **The same one-line gitignore defect bit two different subtrees, weeks
> apart, and in both cases the symptom was source that silently did not exist.** After that merge
> the root rule no longer reaches `options-bot/`, so `quant_bots/.gitignore`'s `!data/`
> re-include is now belt-and-braces rather than load-bearing. Both were re-verified together after
> the merge: all three source files unignored, all 24 state files still ignored.

Where it went wrong was the sentence "The `data/*.py` sources exist only on the Oracle box."
Nobody had looked inside the tracked zips. Four copies existed:

| copy | tracked in git? | sha256 (`universe.py`) |
|---|---|---|
| `options-bot/handoff/quant_bots.zip` | **yes** | `4bdf8ecafeddaf01` |
| `options-bot/quant_bots/options/data/` (main checkout, on disk) | no | `4bdf8ecafeddaf01` |
| `C:\Users\donni\Downloads\options-bot2\...` | no | `4bdf8ecafeddaf01` |
| restored copy in this worktree | **now yes** | `4bdf8ecafeddaf01` |

All three files (`__init__.py`, `earnings.py`, `universe.py`) are byte-identical across all four.
**This was relocation of verified code, not reconstruction, and there is no judgement call
anywhere in it.**

The line that saved the project is `options-bot/.gitignore:34` — `!handoff/*.zip`, a deliberate
negation re-including the handoff archives. Whoever wrote it made the recovery possible.
**Do not tidy it away.** It is now commented to say so.

> **The lesson, stated narrowly because it generalises:** *"the only copy is on machine X"* is a
> claim about where somebody looked, not about where the file is. The zip was 302 KB, in the repo,
> in `git ls-files`, for the entire period the item sat BLOCKED waiting on a human with an SSH key.

## Verification — what was actually checked, in order

**1. The premise, not assumed.** The brief said the missing symbols come from `quant_bots/data/*`.
They come from `quant_bots/options/data/*`; `quant_bots/data/` is the *stock* bots' state
directory and holds no `.py` at all. Those are two different things that collide on the name
`data`, which is the whole reason the gitignore rule did the damage it did. `core/universe_builder.py`
*also* defines `UniverseBuilder`/`UniverseConfig`/`UniverseSnapshot`/`UniverseTicker` for the stock
bots — so "the symbols exist somewhere in the tree" was true and irrelevant. Path equivalence was
not assumed anywhere.

**2. The failure reproduced exactly, before the fix.** With `options/data/` moved aside:

    cd options && python -m unittest discover
    Ran 53 tests ... FAILED (errors=14)      # 14x "No module named 'data'"

That is the documented signature to the digit — `deploy/preflight.py`'s docstring and
`quant_bots/.gitignore`'s comment both say "collects 53 of 181 tests and fails with 14x
`ModuleNotFoundError: No module named 'data'`". Restored, the same command runs **181, OK**.

**3. Symbol by symbol.** Every import of the package across the tree resolves — 6 importing files,
8 import statements, **8 distinct symbol names** (`EarningsCalendar`, `UniverseBuilder`,
`UniverseConfig`, `UniverseSnapshot`, `UniverseTicker`, `LIQUID_ETF_WHITELIST`,
`parse_market_cap`, `parse_price`), checked as 11 module-qualified resolutions because several are
imported both from `data` and from `data.universe`:

    orchestrator/jobs.py:36       from data import EarningsCalendar, UniverseBuilder, UniverseConfig
    screener/screener.py:34,35    from data.earnings / data.universe import ...
    scripts/build_universe.py:29  from data import UniverseBuilder, UniverseConfig
    scripts/screen.py:27          from data import EarningsCalendar, UniverseBuilder
    tests/test_screener.py:8      from data.universe import UniverseSnapshot, UniverseTicker
    tests/test_universe.py:10,176 from data.universe import LIQUID_ETF_WHITELIST, ... parse_price

**4. Signatures against call sites, not just names.** Every dataclass field set was checked against
the keyword arguments actually used at every construction site (`UniverseTicker` 7/7 fields match
at all 8 sites, `UniverseSnapshot` 4/4 at all 4, `UniverseConfig` at all 8), and the two
non-dataclasses were checked against their `__init__` and method call sites:
`EarningsCalendar(unknown_means_safe=...)`, `UniverseBuilder(config, tradier)`, `.build()`,
`.save(snapshot, path)`, `.load(path)`, `.get_next_earnings(symbol)`. **Zero mismatches.** (The
checker also flagged `.save(1 arg)` calls in `account_state.py`, `sim_portfolio.py` and
`risk/state.py` — those are unrelated objects that happen to have a `save` method, correctly
reported as "may be a different object" rather than as a mismatch.)

**5. Git will actually track them this time.** `git check-ignore` returns 1 (not ignored) for all
three files, and `git status` shows the directory as untracked-and-addable. The `!data/`
re-include in `quant_bots/.gitignore` works, and `test_bot_state_is_still_excluded` still passes,
so re-including the source package has not started committing sim books.

## Results

| gate | before | after |
|---|---|---|
| `quant_bots/options` suite | 53 collected, **14 errors** | **181 tests, OK** |
| `quant_bots` core suite | 172, OK | **172, OK** (unchanged) |
| `deploy/preflight.py` | could not pass — `import data` failed | **exit 0, PREFLIGHT OK** |
| main Valquo tree | 24 suites green | **24 suites green, 0 failed** |

All three FIXES.md fixes verify individually on every preflight run, by symbol and by behaviour:
exit orders priced from the full map; an all-oversold cross-section yields 20 longs / 0 shorts;
`Jobs.sim_positions_view` present. **353 bot tests pass.**

## How C6 closes

Its criterion was *each fix deployed, or recorded*. **Deployed is now permanently n/a** — the
service is decommissioned, so there is nothing to deploy to. All three are therefore **recorded**,
and better than the record required: they are re-verified by behaviour on every preflight run
rather than asserted in a markdown file. "Fixed in repo, not deployed" was flagged by the audit as
a *decaying* state; with no service it is a stable one.

## State preserved

`quant_data.tgz` (36 entries, **zero `.py` files** — state only, which independently confirms the
sources question is answered by the zip and not by the tgz) extracted to
`options-bot/quant_bots/data/` **in the primary checkout**, not this worktree, because the worktree
is ephemeral and the point was to keep the record on the machine. 24 files:

* `journal/{trend,momentum,reversion}/` — 6 journals, 2026-06 and 2026-07
* `sim/{trend,momentum,reversion}/` — 3 equity curves + 3 portfolio snapshots, through 2026-07-31
* `reports/` — 9 weekly correlation reports, 2026-06-07 → 2026-08-02
* `state/` — 3 account-state files

Extraction validated every member against path traversal, absolute paths and non-regular files
before writing, and refuses to overwrite differing content. **All 24 are gitignored** (verified
individually with `git check-ignore`; they match `quant_bots/.gitignore:34` etc.), so none can
reach a commit.

## Two commit hazards found and closed

* **`quant_data.tgz` was neither tracked nor ignored** — it sat untracked in the primary checkout,
  one `git add -A` from committing a state archive. `*.tgz` / `*.tar.gz` now ignored in
  `options-bot/.gitignore`, with a comment explaining why `!handoff/*.zip` above it is the
  opposite case and must survive.
* **`valuation-tool/options-bot2/` was neither tracked nor ignored** — a second, older, complete
  copy of the bot tree *inside the repo folder*, with its own `quant_data.tgz`. Same hazard, larger
  payload. Now ignored at the repo root. Kept on disk deliberately: it is a third independent copy
  of the recovered sources.

Pre-existing and deliberately not changed: `handoff/{quant_bots,screener,options_backtest}.zip`
are tracked, by the `!handoff/*.zip` negation. That is the design that just paid for itself.

## Docs swept

Decommission notices added at the top of each, keeping the documents as the record:

* **`options-bot/DEPLOYMENT.md`** — its recommendation ("Stay on Oracle") is marked **void by
  events**, fairly: it named reclamation and silent tier cuts as the risks, and it was right about
  those. It did not anticipate the box vanishing with a source package on it.
* **`options-bot/FIXES.md`** — records that C6 closes on the *recorded* branch. Its stale count
  table is **left stale on purpose**, since the paragraph under it argues that a count is a bad
  freshness proxy; measured values are given in the notice instead.
* **`options-bot/HANDOFF.md`** and **`options-bot/handoff/HANDOFF.md`** — byte-identical copies
  (same sha256 before and after); both updated together and re-verified identical. §7's live
  deployment is marked historical.
* **`options-bot/quant_bots/deploy/deploy.sh`** — comment banner only. **Its logic is untouched
  deliberately:** `tests/test_deploy_preflight.py` asserts against this file's literal text in four
  places, so a casual edit breaks four tests. Re-ran them: 9/9 still pass.

## Nothing in the main tree depended on the box — here is exactly what I checked

362 tracked files outside `options-bot/`, of which 218 are Python and 241 are executable/config:

1. **Box IP / host / `ubuntu@`** — 1 hit, in `HANDOFF_optionsbot.md` (this file, quoting the old
   scp instruction). Zero in code.
2. **`ssh` / `scp` / `systemctl`** — 5 hits, all prose in `HANDOFF_optionsbot.md` and the C6 ledger
   row. Zero in code.
3. **Imports of the bot packages** — checked by **AST, not grep**, across all 218 main-tree Python
   files, for `quant_bots` and for the flat names the bots use (`core`, `data`, `broker`,
   `portfolio`, `risk`, `screener`, `strategy`, `orchestrator`, `trend`, `momentum`, `reversion`,
   `notify`): **0 real imports.** A regex pass had reported one hit at
   `valuation/edge/fundamental_panel.py:681`; it is prose inside a docstring — "computed only from
   data public by `as_of`" — and the AST pass correctly finds nothing.
4. **Bot service units** (`*-bot`, `daily-summary`, `weekly-report`) — 66 hits, every one either a
   `.gitignore` path under `options-bot/` or narrative in `HANDOFF_STATUS.md`. No unit files, no
   invocations.
5. **Bot state paths** (`quant_bots/data`) — 6 hits, all prose in this file and the ledger row.
6. **CI** — all 3 files under `.github/` checked for `options-bot`, `quant_bots`, `ssh`, `scp` and
   the IP: **zero references.** No workflow ever touched the box.

**Conclusion: the main Valquo tree has no executable dependency on the Oracle box.** Valquo runs on
Render from `main` and never talked to it. Decommissioning costs the main product nothing.

## Findings for other lanes — recorded, not repaired

* **`deploy.sh`'s `EXPECTED_CORE_TESTS` is drifting again.** It reads 163; the core suite measured
  **172** on 2026-08-07. Drift 9, inside the 12 that `test_expected_core_test_count_has_not_gone_stale`
  allows, so it passes — but this is the same constant that once sat at 106 against a suite of 148.
  Noted in the banner, **not bumped**: bumping it is a deploy decision and there is no deploy.
* **`tests/test_deploy_preflight.py` has a class named
  `TheOptionsBotCannotBeDeployedFromThisRepo`.** As of today the premise is false — the repo has
  the sources and the preflight passes. Its two tests are about gitignore behaviour and both still
  pass, so nothing is broken; the *name* is now misleading. Renaming a test class is the owning
  lane's call.
* **`options-bot/FINDINGS.md:13`** still says three bugs "are running right now on the Oracle box."
  Left alone — it was not in the sweep list and it is a historical findings document, but a reader
  could take it as current.

## What I deliberately did not do

* **No bot logic was modified.** The only executable file touched is `deploy.sh`, and only its
  comment header. Everything else is markdown or `.gitignore`.
* **I did not delete `options-bot2/` or the archives.** Redundant copies of a package that was
  nearly lost are not clutter; they are why it was recovered. Ignored, not removed.
* **I did not un-track the handoff zips** despite the instruction not to commit archives. They were
  committed long before this task, by a deliberate negation rule, and removing them would delete
  the artifact that made this recovery possible.
* **I did not reconstruct anything.** Had the zip been absent I would have stopped rather than
  invent an earnings filter — `EarningsCalendar.unknown_means_safe` decides whether an unknown
  earnings date lets a trade through, and guessing it wrong fails open.


---

# FOR DON — what to delete, in one line (2026-08-07)

> **Delete `C:\Users\donni\Downloads\valuation-tool\quant_data\`,
> `C:\Users\donni\Downloads\valuation-tool\options-bot2\` and
> `C:\Users\donni\Downloads\options-bot2\` — keep
> `C:\Users\donni\Downloads\valuation-tool\options-bot\quant_data.tgz` as the one archive.**

Everything in those three folders is now either byte-identical to something kept, or an older
revision of a file already in git. Nothing is lost. **The one file that would have been lost has
already been rescued** — see the warning below.

**DO NOT DELETE** `C:\Users\donni\Downloads\valuation-tool\options-bot\quant_bots\data\`. That is
not a copy; it is the live state directory the bots read, and it is gitignored.

| path | what it is | verdict |
|---|---|---|
| `valuation-tool\options-bot\quant_data.tgz` | the state archive | **KEEP — this is the one archival copy** |
| `valuation-tool\options-bot\quant_bots\data\` | live state (24 files, gitignored) | **KEEP — not a copy, this is the working set** |
| `valuation-tool\quant_data\` | loose extracted state | delete — 24/24 byte-identical |
| `valuation-tool\options-bot2\` | old bot tree + its own `quant_data.tgz` + `data_archive\` | delete — after the rescue below |
| `Downloads\options-bot2\` | second copy of the same old tree | delete — after the rescue below |
| `valuation-tool\options-bot\handoff\*.zip` | source recovery artifacts, **tracked in git** | **KEEP — do not delete, this is what saved C6** |

## The consolidation was a no-op, because the premise was wrong — measured, not assumed

The task described `quant_data\` as **fresher** than the tgz archives, holding
`correlation_2026-08-02.md` and journals the tgz copies "stop 2026-07-26" without. **That is not
what is on disk.** Every copy is the same snapshot:

* **All 24 files in `quant_data\` are byte-identical (sha256) to the state already restored during
  C6.** Not one file is newer on either side; no journal record, sim row or report exists in one
  copy and not the other.
* **All three `quant_data.tgz` files are the same archive** — same 26,835 bytes, same outer sha256
  `94014f42f0f9bc17` — in `valuation-tool\options-bot\`, `valuation-tool\options-bot2\` and
  `Downloads\options-bot2\`.
* **All four extracted state directories are identical to each other**: `quant_data\`,
  the restored `options-bot\quant_bots\data\`, and the `data_archive\` in both `options-bot2`
  trees.
* `correlation_2026-08-02.md` (3,873 bytes) **is present in the tgz** and always was — it is in
  the copy restored during C6. The likely source of "stops 2026-07-26" is that
  `correlation_2026-07-26.md` is the second-newest report, so a truncated listing ends there.

**Newest content anywhere, and therefore in the kept copy:** reports through
**2026-08-02**; journals through **2026-07-31** (`trend` 14:30:08Z / 67 records, `momentum`
14:46:21Z / 117, `reversion` 15:01:38Z / 153 for July); sim portfolios and account states
2026-07-31. Seven copies, one snapshot, nothing to merge.

## ⚠ ONE FILE WOULD HAVE BEEN DESTROYED BY THIS CLEANUP — it has been rescued

**`POST_MORTEM.md` (7,957 bytes) existed ONLY inside the two `options-bot2` folders.** It is not
in `options-bot\`, is **not tracked, and has never appeared in this repository's history on any
branch** (`git log --all -- "*POST_MORTEM*"` is empty). Both copies are identical
(sha `1bb8e08dbb03fe66`).

It is not a stale duplicate. It is the **only** analysis of the bots' live SIM period — *"38
trading days of live SIM data, 2026-06-08 to 2026-07-31. Data pulled before the Oracle instance
was terminated"* — and it documents a real failure: mean-reversion finished the window holding
**206 long positions at 285% gross exposure, on margin, in a strategy designed to be
dollar-neutral**, while the weekly report called it 5.5% volatility, Sharpe 0.01 and "effectively
independent (ideal for diversification)". With the box gone, that window can never be reproduced.

**I copied it to `options-bot\POST_MORTEM.md` and committed it, byte-identical.** That is one file
more than this task asked me to commit, and the reason is that the task's deliverable is a
delete list: advising deletion of the only copy of the project's own post-mortem would have been
delivering a broken answer. It is 8 KB of markdown and reverting it is one command. **The state
files were committed as instructed: none.**

*How it was found:* comparing the trees by content alone said "148 of 186 files differ", which is
just the Jul-26 revisions of files that have since moved on — noise. Comparing by **filename**
reduced it to 25, of which 24 are the duplicated state and one is `POST_MORTEM.md`. A
content-only diff would have buried it.

## Third commit hazard closed

`valuation-tool\quant_data\` was untracked **and** unignored at the repository root, so
`git add -A` in the primary checkout would have committed 24 bot state files into the Valquo repo
— the same hazard as `quant_data.tgz` and `options-bot2\`, and the third of its kind found in this
lane. `/quant_data/` is now ignored as a guard until Don deletes the folder. Re-verified after the
change: all 24 canonical state files still ignored, all three recovered source files still
tracked-eligible.

## What was NOT done

* **Nothing was deleted.** Every path above is intact; the cleanup is Don's to run.
* **No state file was committed**, before or after consolidation — verified against `origin/main`
  with `git ls-tree` (`quant_bots/data/`, `*.tgz` and `options-bot2/` return nothing).
* **No file was merged or edited**, because every copy was identical. Had any journal genuinely
  diverged, the right move would have been a union of records rather than "keep the newest file",
  since two partial journals can each hold records the other lacks — that case did not arise.


---

# O16 + O24 — PRE-REGISTRATION (committed 2026-08-07, before any number existed)

**This section was committed in its own commit, with no results in the tree.** The thresholds
below are executable constants in `valuation/edge/options_signals_v2.py`, not prose, so the
verdict rule cannot drift to meet the numbers.

## The question

`term_slope` = `atm_mid` (~60-DTE ATM IV) − `atm_front` (front-expiry ATM IV), computed at
`options_signals_v2.py:230`. It was the strongest single feature in the signal stack.

**The entry signal is measured dead (R2) and nothing here re-opens it.** This characterises the
FEATURE, which still feeds the live Signals surface and is the prerequisite for **U2** (options
surface → stock signals). Two hypotheses, never tested:

* **O16 — is it a front-IV LEVEL in disguise?** If yes, everywhere both are used double-counts
  one exposure.
* **O24 — is it an EARNINGS CALENDAR in disguise?** If yes its information is a date offset, not
  a vol-surface read.

## Data and inference (banked only, no new mining)

`data/options_universe/state_r2_corrected.pkl` — the **R2 corrected** book, explicitly not
`state.pkl` (the void 3,042-trade pre-B1 book). **n = 3,885 trades, 186 names, 118 calendar
months**, `term_slope` coverage 100%. Outcome is `pnl_pct` per trade.

Inference is the options lane's standing method: **date-block bootstrap, block = calendar month**
(`options_stats.date_block_bootstrap`, 2,000 draws, seed 0). Clustering is reported via
`effective_n`, i.e. the design effect **always beside its own shuffled null** — per R3 a raw
design effect is not evidence of clustering.

## The null-vs-null trap, ruled on in advance

R2 measured the entry signal dead, so `term_slope`'s own IC may not be separable from zero here.
**If the raw feature's IC has a date-block CI95 spanning zero, the PREDICTIVE arm is declared
UNINFORMATIVE and carries no verdict weight**, and the IDENTITY arm decides. Committed now
because it would otherwise be tempting to read a null residual IC as "the confound explains it",
when two nulls cannot discriminate between any hypotheses at all.

## O16 protocol and verdict rule

1. **Blocking reproduction gate.** Recompute `atm_front` / `atm_mid` at every alert through this
   module's own `compute_signals` path; recomputed `term_slope` must match the banked value
   within `1e-6` on **≥99%** of rows, or the study stops. Decomposing a quantity we cannot
   reproduce is not evidence about anything.
2. **Identity:** Pearson and Spearman of `term_slope` vs `atm_front` and vs `atm_mid`; variance
   decomposition `var(ts) = var(mid) + var(front) − 2cov`.
3. **Residual:** OLS `term_slope ~ a + b·atm_front`.
4. **Predictive:** Spearman IC vs `pnl_pct` for `term_slope`, `−atm_front`, and the residual.
5. **No-new-data control** (the PEAD template): rank by `−atm_front` alone, keep the top
   **40.6%** — `term_slope`'s own shipped retention — and compare the uplift via
   `date_block_diff`.

**Verdict, first match wins:** **IS THE LEVEL** if `|ρ(ts, atm_front)| ≥ 0.80` **and**
`var(atm_front)/var(ts) ≥ 0.60`; **IS DISTINCT** if `|ρ| < 0.60` **or**
`var(atm_mid)/var(ts) ≥ var(atm_front)/var(ts)`; **otherwise NULL**. Ambiguous is a NULL, not a
lean.

## O24 protocol and verdict rule

1. Days-to-next-earnings from **EVENTS code 22** (`data_providers.earnings_dates`) — the same
   point-in-time source the PEAD study used.
2. **Eligibility, committed before any outcome was seen:** an alert counts only if its next
   earnings date is **within 120 days**. EVENTS coverage is partial (157/186 names; 3,495/3,885
   alerts carry a forward date) and the scoping pass saw an apparent **3,004-day** gap — a hole
   in the calendar, not an eight-year earnings drought. Scoring those as "far from earnings"
   would load the test toward *"not a calendar"*, **the answer this lane would find more
   convenient**. Excluded as UNKNOWN, count reported.
3. Buckets 0-7 / 8-14 / 15-30 / 31-60 / 61-120 days, with counts.
4. **Model:** OLS `term_slope ~ bucket dummies`; statistic is **R²**, the share of `term_slope`'s
   variance the calendar alone reconstructs.
5. **Direction, pre-committed:** the mechanism requires `term_slope` most negative closest to
   earnings, i.e. `Spearman(ts, days) > 0`. **A significant wrong-sign slope refutes the
   mechanism whatever R² says.**
6. **No-new-data control:** keep only alerts >30d from earnings; does that replicate the
   `term_slope` filter's book gain?

**Verdict, first match wins:** **IS THE CALENDAR** if `R² ≥ 0.25` **and** `ρ(ts, days) > 0` with
a date-block CI95 excluding zero; **IS DISTINCT** if `R² < 0.10`; **otherwise NULL**.

## What no outcome here can do

None of this revives the entry signal (R2 stands) and none of it is a claim about live trading.
A confirmed confound means the feature is redundant with something cheaper; a distinct verdict
means U2 may treat it as its own read.

**Logged to `RESEARCH_LOG.md`** as O16 (n=5) and O24 (n=4), domain `options`, verdict PENDING.
Options-domain `N` 155 → **164**; equity `N` unchanged at 121 (`N` is domain-scoped, per M1).

> Read the equity figure as *"these nine trials did not touch it"*, not as a current reading.
> Measured after merging `origin/main` at the end of this cycle: options **164** (unchanged, as
> claimed), equity **129**, project total **296** — equity moved because a concurrent lane landed
> rows, which is exactly the domain scoping working. **`N` is a project quantity that keeps
> rising; re-measure it rather than quoting a number from a handoff.**


---

# O16 + O24 — RESULTS (2026-08-07). One NULL, and one study that stopped at its own gate.

Pre-registration is the section immediately above, committed at `ad66468` with no results in the
tree. Every threshold quoted below was already in `options_signals_v2.py` before any number
existed. **Neither outcome re-opens the entry signal; R2 stands.**

| item | verdict | the one-line reason |
|---|---|---|
| **O16** — is term_slope a front-IV level? | **STOPPED AT THE REPRODUCTION GATE — no verdict** | the banked book is only 86.4% reproducible, because the chain store moved underneath it |
| **O24** — is term_slope an earnings calendar? | **NULL** | R² 0.2144, CI95 [0.183, 0.248] — wholly below the committed 0.25 bar — and the pre-committed direction test spans zero |

## O16 — the gate fired, and what it caught is worth more than the hypothesis was

The pre-registration made the reproduction check **blocking**: recompute `term_slope` from the
banked chains through this module's own `compute_signals`, and require a match within `1e-6` on
**≥99%** of rows, *"or the study stops — a decomposition of a quantity we cannot reproduce is not
evidence about anything."*

**Measured: 3,358 of 3,885 rows reproduce, 86.435%. The gate fails. O16 carries no verdict.**

The cause is attributed rather than guessed, and the attribution is unusually clean:

| | reproduced | mismatched | reproduce rate |
|---|---|---|---|
| chain file **unchanged** since the book was banked | **3,127** | **0** | **100.00%** |
| chain file **re-mined** since | 231 | 527 | 30.47% |

**Every single mismatch sits in a re-mined file; not one sits in an unchanged file.** Median
absolute difference across all rows is exactly 0.0 and the maximum is 0.463. The recompute is
correct wherever its input is unchanged — what moved is the data, not the code.

### BUG — the authoritative options book is not reproducible from the chain store

`data/options` is a **live** store: `theta_bulk` keeps mining and rewrites `TICKER-YEAR.pkl` in
place. **19.5% of the alerts' ticker-year files were rewritten after `state_r2_corrected.pkl` was
banked on 2026-08-05 19:51.** Consequences, in order of how much they should worry someone:

1. **Any recompute-based audit of the corrected book silently disagrees with it on ~13.6% of
   rows** — and would have looked like a code defect rather than a data-drift one. This study only
   caught it because the gate was pre-registered as blocking; a softer check would have been
   waved through as "close enough" and the O16 verdict would have been computed on a mixture of
   two different chain vintages.
2. **`term_slope` and the legs would not even be self-consistent within a mismatching record:**
   the banked `term_slope` comes from the old chain, a recomputed `atm_front`/`atm_mid` from the
   new one, so `atm_mid − atm_front ≠ term_slope` in the same row.
3. **The equity side already solved this and the options side did not.** There is a
   `data/backtest_freeze_2026-08/` with a verified freeze and legend (audit D10). **Option chains
   have no equivalent pin.** That asymmetry is the actual defect; the drift is its symptom.

**Not repaired here, deliberately** — the fix lives in `theta_bulk.py`, which this cycle's
carve-out explicitly excludes ("NOT `theta_bulk.py` — the miner is live in it"), and a freeze
design is a decision for whoever owns the miner, not a patch to smuggle into a study lane. Filed
with file and figures so it can be actioned.

### EXPLORATORY — no verdict, and it must not be quoted as one

Restricting to the **3,358 rows that reproduce exactly** and running the committed protocol. The
subset is defined by chain-file mtime, which is independent of `pnl_pct` and of `term_slope`, but
it is still a post-hoc restriction chosen **after** seeing the gate fail, so it cannot settle a
pre-registered question. Representativeness was checked rather than assumed — it keeps **all 186
names** and 117 of 118 months; mean `pnl_pct` 3.57% vs 2.36% on the dropped rows, mean
`term_slope` −0.0346 vs −0.0387, mean `iv` 0.3073 vs 0.2937.

**Identity.** `Spearman(term_slope, atm_front)` **−0.5405**, date-block CI95 [−0.576, −0.501].
`Spearman(term_slope, atm_mid)` **−0.0064**. Variance decomposition: `var(ts)` 0.02153,
`var(atm_front)` 0.04072, `var(atm_mid)` 0.01389, `cov` 0.01654 — shares **1.891 front**, **0.645
mid**, **−1.536** for the −2cov term. The shares exceed 1 because the legs are strongly
co-moving (`Spearman(front, mid)` +0.787) and differencing two correlated series leaves less
variance than either leg carries; that is why the cross term is reported rather than folded into
a leg.

> **The rule said Spearman and it mattered.** `Pearson(term_slope, atm_front)` is **−0.8167**,
> which is *past* the 0.80 level bar, while Spearman is −0.5405, which is *below* the 0.60
> distinct bar. Same data, opposite branch. The pre-registration named Spearman, so Spearman
> governs — and had the statistic been left to be chosen afterwards, this is precisely where the
> choice would have been made with the answer visible.

**Predictive — and the pre-registered escape clause did not need to fire.** The pre-registration
anticipated a null-vs-null trap (R2 having measured the entry signal dead) and ruled in advance
that a raw IC spanning zero would make this arm uninformative. It does not span zero:

| arm | Spearman IC vs `pnl_pct` | date-block CI95 | excludes 0 |
|---|---|---|---|
| `term_slope` | **+0.0645** | [+0.0271, +0.1024] | yes |
| `−atm_front` | +0.0148 | [−0.0340, +0.0648] | **no** |
| **residual (ts ⟂ atm_front)** | **+0.0774** | [+0.0344, +0.1192] | yes |
| `atm_mid` | +0.0368 | [−0.0118, +0.0854] | no |

**The orthogonal remainder predicts BETTER than the raw feature, and the front leg alone predicts
nothing.** That is the opposite of the confound signature. *(This does not contradict R2: R2
asked whether the alert's day-selection beats random entry; this is a cross-sectional IC among
alerts already generated. Different objects, and neither rescues the other.)*

**No-new-data control.** `term_slope ≥ 0.0105` retains 40.5% and lifts mean pnl **+6.02pp**, CI95
[+1.51, +10.21], excluding zero. The same-sized lowest-front-IV selection lifts **+2.44pp**, CI95
[−2.49, +7.20], **including** zero. The two selections overlap on only **22.0%** of names.

On this subset the committed rule **would** have returned **IS DISTINCT** (|ρ| 0.5405 < 0.60).
**That is not the verdict.** O16 needs a pre-registered re-run against pinned chains.

Clustering, reported beside its own shuffled null per R3: design effect **2.032** vs null p95
**1.224**, `clustering_measurable` true.

## O24 — NULL, and the way it fails is the informative part

**n = 3,458 eligible** (89.0% of the book), 157 names, 118 months. Excluded before any outcome was
seen: 390 alerts whose name has no EVENTS coverage, 37 whose next earnings is beyond 120 days.

| bucket | n | mean `term_slope` | median | mean pnl |
|---|---|---|---|---|
| **0-7d** | 532 | **−0.1916** | −0.0758 | +5.25% |
| 8-14d | 248 | +0.0098 | +0.0212 | +18.41% |
| 15-30d | 604 | +0.0172 | +0.0269 | +12.90% |
| 31-60d | 984 | +0.0038 | +0.0156 | +0.28% |
| 61-120d | 1090 | −0.0311 | −0.0139 | −2.07% |

* **R² = 0.2144**, date-block CI95 **[0.183, 0.248]** — the **entire interval** lies below the
  committed 0.25 bar, so this is a clean miss rather than a coin-flip.
* **Direction: Spearman(term_slope, days) = +0.0018**, CI95 [−0.051, +0.055] — spans zero.
  (Pearson is +0.1654, which is why the rank statistic being named in advance mattered again.)
* By the committed rule — R² below 0.25, direction not significant — **NULL**.

**The earnings mechanism is real, and it is a spike rather than a gradient.** `term_slope` in the
0-7 day bucket is −0.1916, an order of magnitude away from every other bucket, which is exactly
the predicted pre-earnings front-IV inflation. But it is **non-monotone**: the relationship rises
to 15-30d and falls again by 61-120d. A monotone rank test is close to blind to that shape, which
is how R² can nearly clear while the direction test reads zero.

**That is a finding about my own design, not a reason to move the verdict.** The direction test
was committed before any data was seen; a shape-agnostic direction test (or an explicit
0-7d-versus-rest contrast) would have been the better instrument, and choosing it *now* would be
selecting the statistic on the result. **Session 11 pre-registers that contrast or nobody quotes
it.**

**The no-new-data control runs the other way.** Keeping only alerts >30 days from earnings makes
the book **worse**: −0.95% against +3.81% on the eligible book, diff **−4.76pp**, CI95 [−7.59,
−2.10], excluding zero. Near-earnings alerts (≤30d) return **+10.95%**. So the earnings calendar
is not a cheap redundant copy of `term_slope` — it is a *different* sort, and on this book a
better one. Clustering: design effect **2.1496** vs null p95 **1.2086**, measurable, and
consistent with R3's 2.2121 on the full book.

## What each verdict does downstream

* **The live Signals surface** (`options_live.py:37` documents `term_slope` with its 0.0105
  threshold). **Nothing changes.** O24 is a NULL and O16 has no verdict, so there is no
  measured basis for removing, reweighting or renaming the feature. The one thing that would
  have justified action — "it is just the front IV, delete one of them" — is precisely what did
  not get established.
* **U2 (options surface → stock signals), which is queued behind this question.** It is **not
  unblocked**, and the honest statement of why is now sharper than "untested": the earnings-
  calendar confound is ruled out at the ≥25%-of-variance level (O24), while the front-IV-level
  confound is **unresolved** and cannot be resolved against a mutable chain store. **U2's real
  prerequisite is the chain freeze, not another study.**
* **Anything that recomputes from `data/options`** should treat the chain store as a moving
  target until it is pinned, and should carry a reproduction gate. That is the transferable
  part of this cycle.

## BUGS FOUND

1. **The options chain store is mutable and the authoritative book is not reproducible from it**
   (detail above). 19.5% of alert ticker-years re-mined post-bank; 86.4% reproduction against a
   99% requirement; 100.00% on unchanged files. **Owner: whoever owns `theta_bulk.py`** — out of
   this cycle's carve-out by name. The equity side's `data/backtest_freeze_2026-08` + D10 legend
   is the model to copy.
2. **`compute_signals` discarded both legs of its own difference.** `atm_front` and `atm_mid`
   were computed and thrown away, keeping only `term_slope`, so **no banked book has ever
   carried the inputs to its own strongest feature** — which is the entire reason O16 needed a
   ~18-minute full re-derivation from chains instead of a lookup. Now emitted additively (no
   existing key changes, no banked result moves), so the next book carries them.
3. **A structural zero is indistinguishable from a flat term structure.** `mid_exp` is the expiry
   nearest 60 DTE *among those after `as_of`*; when the nearest expiry is itself closest to 60,
   both legs are the same contract and `term_slope` is identically 0.0. **It does not fire on
   this book (0 of 3,885)**, so nothing is affected — recorded because it is invisible in the
   stored data and would be indistinguishable from a genuine reading if a sparser universe were
   ever mined. Pinned by
   `test_when_the_60_dte_pick_lands_on_the_front_expiry_the_slope_is_zero`.

## What I did NOT do

* **I did not repair the chain drift.** It is `theta_bulk.py`, excluded by name from this
  cycle's carve-out, and a freeze design is the miner owner's call.
* **I did not let O16 return a verdict.** The exploratory subset would have said IS DISTINCT and
  it would have been the *convenient* answer for a lane that wants U2 unblocked. The gate was
  pre-registered as blocking; honouring it only when it agrees with you is not honouring it.
* **I did not re-cut O24's direction test** to the shape that fits the effect, though the spike
  at 0-7d is plain in the table. That is selecting the statistic on the result.
* **I did not touch `theta_bulk.py`, `valuation/screener|engine|web/**`, or anything outside the
  six options files this cycle carved out.** `check_lanes.py O16 O24` reports a HARD collision
  between the two items on `options_signals_v2.py` — irrelevant here because one agent ran both
  in sequence, and noted so nobody reads the clean landing as evidence the checker was wrong.
  Both dependencies were verified landed first (O16 needs B1, O24 needs D10; both DONE).
* **I did not re-run the miner or mine anything new.** Banked data only, as scoped.

## Reproduce

    python tests/test_term_slope_decomp.py        # 38 tests: the statistics, the committed
                                                  # verdict rules, the reproduction gate

---

# 2026-08-08 — FREEZE THE CHAINS: the store moved under the banked book, and now it cannot do so silently

**Out-of-band instrument repair.** This is my own O16 finding promoted to its own task: O16's
blocking reproduction gate measured the authoritative options book at **86.435% reproducible**
against the chain store it was built from, and the cause was not a code defect but a mutable
store. Every banked options verdict was pinned to inputs that no longer existed.

## The freeze design, and the measurement it was chosen on

The brief named two candidate designs and required that **(a) be measured before it could be
rejected** — a good instruction, because the intuition here is wrong by two orders of magnitude.

| | |
|---|---|
| (a) frozen copy of the chain rows the R2 book consumed | **157.88 MB** pickle, **27.44 MB** gzipped, 2,870,079 rows |
| live store it is drawn from | **26.98 GB**, 5,063 symbol-years, 1,000 symbols |
| **(a) as a share of the store** | **0.585% pickle / 0.102% gzipped** |

**So (a) is ADOPTED, not rejected.** The reason it is cheap is worth stating because it is the
non-obvious part: **a book is SPARSE in the store.** 3,885 trades read one *day* out of ~250 per
symbol-year, plus one contract's history each — not the years themselves. The breakdown is
2,717,072 alert-day slice rows + 158,702 contract-history rows, deduplicated to 2,870,079.

**The artifact actually banked is smaller still: 23.30 MB over 2,870,811 rows — 0.086% of the
store.** It is smaller than the 27.44 MB probe *despite* 732 more rows and an extra `symbol`
column, and the reason is worth stating rather than glossing: the probe kept the concatenation's
non-contiguous index (a 2.87M-entry int64 array) and `freeze_book` drops it. The extra rows come
from that same `symbol` column — rows identical across two symbols correctly stop collapsing
into one another.

**(b) fingerprinting is adopted alongside it, not instead of it**, because the two answer
different questions: (a) is *"can this verdict still be checked"*, (b) is *"is what I am reading
now what was read then"*. Only (b) can make drift loud, and only (a) survives the store being
deleted.

**THE LIMIT THAT MUST TRAVEL WITH (a):** the frozen copy is **trade scope**. `chain_on` is called
on every *candidate* day the scan looks at — **33,254** of them for this book against 3,885
alerts — so the freeze replays every per-trade statistic but **cannot re-derive which alerts
fire**. Run scope is *estimated* at ~1,280 MB (699.6 mean rows/day-slice × 33,254 × 55.01 B/row);
that is an extrapolation, not a measurement, and is labelled as one wherever it appears.

Reproduce the cost measurement: `python -m scripts.options_freeze_cost`.

## Per-book reconciliation, and the pattern nobody had looked for

Measured against the store as it stands today. "Untouched" is the share of the symbol-years a
book consumed whose files have **not** been rewritten since that book was banked — the necessary
condition for reproducibility, and cheap enough to run on every book.

| book | banked | symbol-years | rewritten since | untouched |
|---|---|---|---|---|
| **R2 corrected (authoritative)** | 2026-08-05 19:51 | 1,429 | 280 | **80.41%** |
| control r2 seed0 | 2026-08-05 20:01 | 1,371 | 277 | 79.80% |
| control r2 seed1 | 2026-08-05 20:21 | 1,381 | 269 | 80.52% |
| control r2 seed2 | 2026-08-05 21:14 | 1,384 | 246 | 82.23% |
| control r2 seed3 | 2026-08-05 21:26 | 1,372 | 248 | 81.92% |
| control r2 seed4 | 2026-08-05 21:38 | 1,358 | 244 | 82.03% |
| pre-correction `state.pkl` | 2026-08-03 08:28 | 1,251 | 547 | **56.27%** |
| `state_mid.pkl` | 2026-08-03 09:41 | 1,251 | 547 | **56.27%** |
| entry lab | 2026-08-03 17:36 | 1,481 | 648 | **56.25%** |
| exit lab | 2026-08-03 19:05 | 1,448 | 622 | **57.04%** |

**THE FINDING THE BRIEF DID NOT ANTICIPATE: drift is PROGRESSIVE, and it is a function of age.**
Every book banked on 2026-08-03 sits at ~56% untouched; every book banked on 2026-08-05 sits at
~80%. This is not a property of the R2 book — it is a property of *time spent sitting next to a
live miner*. O16 caught it on the newest and most-defended book in the project, which is the
best case, not the worst.

**Two facts that bound the damage, both measured rather than assumed:**

* **Nothing is lost.** `absent_from_store` is **0** for all ten books — no consumed symbol-year
  has been deleted. Drift is rewriting, not deletion.
* **The store has been quiet since 2026-08-06 04:29:39**, the newest mtime among every consumed
  file across all ten books. So the snapshot frozen today is coherent, and the drift all happened
  in the window between the banks and that timestamp.

### Dispositions

| book | disposition |
|---|---|
| R2 corrected | **REFROZEN** — new bank at `data/options_freeze/R2_CORRECTED_2026-08-08/` (`chains.pkl.gz` + `FREEZE_MANIFEST.json`). Never an overwrite: `freeze_book` refuses to land on an existing freeze. |
| control seeds 0-4 | **REFROZEN**, at `data/options_freeze/R2_CONTROLS_2026-08-08/` — **21,877,728 rows, 168.9 MB**, all five seeds (29,785 trades), 1,558 symbol-years. The R2 verdict is a *comparison* carried by the paired name-year sign test, so freezing the real book alone would leave half of it un-replayable. **It took three attempts and the first two failed; see "A performance defect in my own freeze" below — the intermediate states of this row are recorded there rather than tidied away.** |
| pre-correction, `state_mid` | **RETIRED**, annotated: *inputs no longer reproducible; the verdict stands on the frozen summary.* Both were already SUPERSEDED by the B1-B4/B15 corrections — the record's own word — so refreezing would preserve replayability for books nobody may quote. |
| entry lab, exit lab | **RETIRED**, annotated the same way, at 56.25% / 57.04%. A refreeze remains possible and cheap should either be quoted again; what it would freeze is *today's* store, which is not what those books were scored against. |


## The gate, and where it is wired

`valuation/edge/options_freeze.py` (new) + one check inside `theta_bulk._year_frame`.

**Bank time is DESCRIPTIVE. Replay is BLOCKING.** That asymmetry is the design, not a compromise:
a stamp that could fail the run it describes would be switched off within a week, and the miner
must stay free to re-pull faulted years. Unpinned is the default and costs one `is not None` test
per frame load.

* `stamp_years()` / `stamp_run()` — fingerprint every symbol-year a finished run consumed.
  Wired into **all three** banked-book runners: `optuniv_run.py`, `optentry_run.py`,
  `optexit_run.py`, each writing `CHAIN_STAMP.json` beside the book. It cannot raise: it runs
  *after* the scoring is banked, so a bookkeeping bug must never destroy finished work — pinned
  by a test that forces an internal failure.
* `replay_pin()` — installs a banked stamp; `_year_frame` then **refuses** to serve a symbol-year
  whose bytes differ. Checked **before** the unpickle and before the memo cache, because serving
  a drifted year once would leave the wrong rows in `self._mem` for the rest of the process
  (pinned by its own test).
* Absent from the stamp is **not** a violation — it means this replay never read that year.
  "We read nothing here" and "we forgot to record this" must not look the same, so an absent
  symbol-year is *recorded* as `present: false` rather than omitted.

**Fingerprints are two-level, so the stamp does not cry wolf.** A byte sha256 (memoised in a
`.sha256` sidecar keyed by size+mtime_ns, so 27 GB is not rehashed per read) catches everything
but is too sensitive: re-pickling identical rows under a different pandas version changes the
bytes and nothing else. A stamp that fires on *that* trains the reader to ignore it. So a byte
mismatch escalates to a content comparison, which separates `repickled` (benign) from `changed`
(the O16 failure). Where no content record was banked, the verdict is reported as
`changed_or_repickled` — undecided, never guessed in either direction.

**Two corrections I made to my own design mid-task, both kept in the record:**

1. `content_digest` first rendered each frame with `to_csv`, which made banking a **~50-minute**
   step (1,429 whole year-frames, ~285M rows of text formatting). Now hashed from the column
   buffers. This is not just convenience: **a freeze slow enough to be annoying is a freeze that
   gets skipped, which is exactly how the store came to move under the book.**
2. More important — a whole-year digest is **over-broad**. It reports `changed` when a re-mine
   rewrites rows on dates the book *never read*, which is not a fact about that book's inputs.
   `verify_against_frozen()` asks the precise question instead: *are the rows this book actually
   consumed still identical?* The frozen copy already **is** that content record, so the
   expensive whole-year digest buys nothing the freeze does not provide, and the banking path is
   byte-stamp + frozen copy. `content_digest`/`deepen_stamp` remain for whole-year comparisons
   and stay pinned by tests.

`tests/test_options_freeze.py` — 40 tests. The ones that earn their place pin failures that
would otherwise be **silent**: a sidecar surviving a rewrite, a pin that fails open, a digest
that cannot tell a re-pickle from a data change, a drifted year lingering in the memo cache, and
drift reported for dates the book never read.


## O16 — the verdict it could not carry: **IS DISTINCT**

### The object of study changed, and that is stated rather than slipped in

The register (`ad66468`, **unamended** — every constant as committed) gates on *"recomputed
`term_slope` matches the BANKED value on ≥99% of rows."* **That gate cannot be made to pass, ever.**
The banked book's inputs for the 13.6% of rows whose chain files were re-mined no longer exist
anywhere; re-running the comparison returns the same 86.435% in perpetuity. Measured again today,
it does exactly that:

    compared 3,885; identical within 1e-6: 3,358 (86.435%); median |diff| 0.0; max 0.4633

So the question is answered about the **refrozen book**: `atm_front`, `atm_mid` and `term_slope`
recomputed together from one frozen store, hence mutually consistent **by construction** rather
than by a gate. Three consequences, all of which cut in different directions and all of which are
reported:

* **It is the LIVE feature.** This is what `compute_signals` returns today, on today's store — so
  it is the object the Signals surface and U2 actually care about, arguably more relevant than a
  book banked three days ago.
* **The banked-book version of the question is permanently unanswerable.** Not "not yet answered".
* **I had already seen an exploratory version of this answer last cycle**, on the 86.4% subset.
  The re-run was therefore **not blind**, and that is the honest reason the trial cost is paid
  again below rather than waived as a mere repair.

The recompute covered **3,885 of 3,885 rows (100% of the book), 186 names, 118 months, 0 errors,
0 drift**, run under `replay_pin` — and the pin was independently re-verified afterwards with the
corrected uncached hash path: **1,429 of 1,429 symbol-years clean in 18.2s**. "The store held
still during the run" is a measured fact here, not an assumption.

### Identity — the arm the register says decides

| statistic | value | date-block CI95 |
|---|---|---|
| **Spearman(term_slope, atm_front)** | **−0.53966** | **[−0.5740, −0.5022]** |
| Pearson(term_slope, atm_front) | **−0.82793** | |
| Spearman(term_slope, atm_mid) | −0.00831 | |
| Spearman(atm_front, atm_mid) | +0.79093 | |
| var(atm_front)/var(ts) | 1.88319 | [1.7703, 2.0267] |
| var(atm_mid)/var(ts) | 0.61088 | |
| −2cov share | −1.49406 | |

**VERDICT: IS DISTINCT.** `|ρ| = 0.5397` fails the LEVEL bar of 0.80, and falls **below** the
DISTINCT bar of 0.60 — and the whole CI95 sits inside that region, so the verdict is not a
sampling accident.

**THE VERDICT HINGES ENTIRELY ON THE PRE-REGISTERED CHOICE OF SPEARMAN, AND THAT MUST BE QUOTED
WITH IT.** On **Pearson** the correlation is **−0.828**, which clears the LEVEL bar of 0.80, and
`var(atm_front)/var(ts) = 1.88` clears its 0.60 companion — so the *same data* under Pearson
returns **IS THE LEVEL**, the opposite verdict. The register named Spearman in writing before any
number existed, so IS DISTINCT stands; but anyone quoting this must know the answer flipped on a
choice made in advance. The gap between the two is itself the finding: the relationship is
strongly *linear* and much more weakly *monotone*, i.e. a few large-magnitude alerts carry the
linear fit.

**Variance shares exceed 1 because the legs co-move** (Spearman(front, mid) = +0.791): the
identity is var(ts) = var(mid) + var(front) − 2cov, and the −1.494 cross term absorbs the excess.
Read alone, "atm_front is 188% of term_slope's variance" would be a nonsense claim for the level
hypothesis — it is only interpretable beside the covariance term.

### Predictive — informative this time, and it corroborates DISTINCT

The register's null-vs-null escape clause did **not** fire: the raw feature's own IC excludes zero,
so the residual comparison is admissible.

| arm | IC (all 3,885) | CI95 | excludes 0 |
|---|---|---|---|
| `term_slope` | +0.05673 | [+0.0206, +0.0922] | yes |
| **residual(ts ~ atm_front)** | **+0.07034** | [+0.0287, +0.1131] | **yes** |
| `−atm_front` | +0.01316 | [−0.0333, +0.0626] | no |
| `atm_mid` | +0.03406 | [−0.0151, +0.0814] | no |

**The part of `term_slope` orthogonal to front IV predicts BETTER than `term_slope` itself, and
front IV alone predicts nothing.** That is the opposite of a confound signature — a disguised
level would put the predictive content *in* the level. The unchanged-chain subset (n=3,358) agrees
throughout: +0.0645 / **+0.0770** / +0.0148 / +0.0368.

*Caveat that travels with this arm:* `pnl_pct` is **banked** (a trade outcome) while `term_slope`
is **refrozen**, so for the 13.6% of drifted rows the two come from different stores. That is why
the unchanged-only subset is reported beside it; it does not change the reading.

## O24 — re-checked on the refrozen feature, and the NULL is re-confirmed

The brief asked whether a materially different refrozen book forces O24 to be re-checked. It was
re-run rather than reasoned about:

| | banked (last cycle) | **refrozen** |
|---|---|---|
| eligible n | 3,458 | **3,458** (157 names, 118 months) |
| R² on earnings buckets | 0.21443 | **0.21555**, CI95 [0.1840, 0.2498] |
| Spearman(ts, days) | +0.00183 | **+0.00579**, CI95 [−0.0453, +0.0586] |
| verdict | NULL | **NULL** |

| bucket | n | mean ts (refrozen) | mean ts (banked) |
|---|---|---|---|
| 0-7d | 532 | **−0.19120** | −0.19159 |
| 8-14d | 248 | +0.00913 | +0.00976 |
| 15-30d | 604 | +0.01657 | +0.01717 |
| 31-60d | 984 | +0.00515 | +0.00379 |
| 61-120d | 1,090 | −0.03015 | −0.03112 |

**The answer to the brief's question: the refrozen book differs materially ROW BY ROW and barely
at all IN AGGREGATE.** 13.6% of individual rows moved, some by as much as 0.463 — yet every
bucket mean shifts by ≤0.0014, R² by +0.0011, and the whole CI still sits below the 0.25 bar. The
0-7d spike, the non-monotone shape, and the reason the monotone direction test is near-blind to
it are all unchanged. **O24's NULL did not need re-checking, and now that is measured rather than
assumed.**


## What these verdicts do downstream

* **The LIVE Signals surface: nothing changes today.** `term_slope` feeds it, and IS DISTINCT
  says the feature is not a redundant restatement of front-month IV — which is a reason **not**
  to remove it, not a reason to lean harder on it. R2 stands: the options entry signal is dead as
  a day-selection edge, and no result here revives it.
* **U2 (options surface → stock signals) is UNBLOCKED on the question it was queued behind.**
  That question was *"is `term_slope` its own read, or front IV wearing a second name?"* and the
  answer, on the pre-registered rule, is that it is its own read. **Two conditions travel with
  that clearance and neither is optional:** (1) the verdict flips to IS THE LEVEL under Pearson,
  so U2 must not be built on a linear-only treatment of this feature; (2) the clearance is for
  the **refrozen/live** feature, not for the banked book.
* **What is now unblocked that was NOT before: replayability.** Before today no options verdict
  could be re-checked against its own inputs. The R2 book and its five controls now can be, and
  every future banked run stamps itself automatically.

## BUGS FOUND

1. **THE SIDECAR HASH CACHE HAS A FALSE-NEGATIVE MODE, AND IT WAS ON THE BLOCKING PATH.**
   `file_sha256` memoises in a `.sha256` sidecar keyed by `(size, mtime_ns)`. **A rewrite that
   produces a file of the SAME SIZE within the filesystem's timestamp granularity collides with
   its own cache entry and the STALE hash is served** — so a drifted chain would have been
   reported clean by the very gate built to catch it. Found by my own test suite failing
   intermittently under load; reproduced deterministically with `os.utime`. **Fixed**: every
   blocking path (`replay_pin` via `_year_frame`, and `verify_stamp`) now passes
   `use_cache=False`; the cache is trusted only for bulk stamping, where a miss costs time
   rather than correctness. The measured cost of the fix is small — uncached verification of all
   1,429 symbol-years took **18.2s**. Two tests pin it, and the older test whose overly broad
   claim ("any rewrite invalidates the sidecar") was simply false has been narrowed to the part
   that holds.
   *Note the ordering honestly: the legs recompute ran BEFORE this fix, so its pin used the
   cached path. That is why the stamp was re-verified afterwards with the corrected path — 1,429
   of 1,429 clean — rather than left resting on the weaker guarantee.*

2. **`freeze_book` has no progress output, and on a 27 GB store that is a real defect.** The R2
   freeze ran 1,153s with a single line printed at the start; while another lane's four
   `x7_reconcile` shards were competing for the machine there was no way to distinguish "slow"
   from "hung" except by inspecting process memory. I did not fix it — it is cosmetic against the
   correctness work in this cycle — but a long-running bank step that cannot be observed is one
   that gets killed and restarted, which I did twice today.

3. **STILL OPEN, unchanged from last cycle and NOT fixed here: run-scope replay.** No banked
   options book can have its *alert selection* re-derived, only its per-trade statistics
   replayed. The freeze covers trade scope only (33,254 candidate days vs 3,885 alerts). This is
   a stated limit of the design, not an oversight, but it means "reproduce the book from
   scratch" remains impossible for every book in the project.


## What I did NOT do

* **I did not re-run the miner or pull anything new.** The freeze is a copy of what was already
  on disk; `data/options` is otherwise untouched apart from the `.sha256` sidecars, which are
  invisible to every file-listing helper in `theta_bulk` (verified: `cached_years('AAPL')` still
  returns exactly its ten years).
* **I did not refreeze the pre-correction book, `state_mid`, the entry lab or the exit lab.**
  Their dispositions are RETIRED-with-annotation and the reasoning is in the table above. What a
  refreeze would capture today is *today's* store, which is not what those books were scored
  against — it would manufacture the appearance of reproducibility rather than the fact of it.
* **I did not freeze RUN SCOPE for any book.** Only trade scope. So no banked book can have its
  *alert selection* re-derived, only its per-trade statistics replayed. The ~1,280 MB figure for
  run scope is an estimate and was not paid.
* **I did not retro-fit stamps onto the already-banked books.** A stamp taken today records
  today's bytes, which for the drifted years are *not* the bytes those books read; writing one
  would be worse than having none, because it would look authoritative.
* **I did not change any live signal, any threshold, or the deployed product.** Nothing here
  touches `valuation/screener|engine|web/**`.
* **I did not amend the O16/O24 pre-registration** (`ad66468`). Every constant is as committed.

## Reproduce

    python -m scripts.options_freeze_cost            # the (a)-vs-(b) cost measurement
    python tests/test_options_freeze.py              # 40 tests: fingerprints, gate, freeze
    python tests/test_term_slope_decomp.py           # 38 tests: the O16/O24 statistics

## The freeze is validated as USABLE, not merely present

An artifact that exists but cannot actually replay anything is decoration, so this was checked
rather than assumed. `validate_frozen.py` loads **only** the frozen copy — never the live store —
and pushes a spread sample of real banked alerts back through `compute_signals`:

    frozen rows 2,870,811   columns [expiration, strike, right, date, bid, ask, volume,
                                     open_interest, symbol]   distinct symbols 186
    sampled 20 alerts: 20 reproduce, 0 missing, 0 mismatched     VERDICT: USABLE

Every sampled alert's `term_slope` recomputed **from the frozen copy** matches the value
recomputed from the store to within `1e-6`. So the R2 book's verdicts can now be re-derived even
if `data/options` is deleted, re-mined, or moved — which is the property that did not exist
before today and whose absence is the whole reason O16 stopped.

## A performance defect in my own freeze, and what it cost

**`freeze_book` scanned the whole year frame once PER CONTRACT.** That is tolerable for the R2
book — 3,885 contracts, 1,153s — and hopeless for the five pooled control seeds: **29,785
contracts × a ~200k-row scan each**. It ran ~45 minutes without emitting a row and was killed by
the environment before writing anything.

Two things follow, and the second is the one worth keeping:

1. **Nothing was corrupted.** `freeze_book` writes to `.tmp` and `os.replace`s, so a kill at any
   point leaves either the previous artifact or nothing. The directory was simply empty. That is
   the atomic-write discipline `theta_bulk` already applies to the store, applied here.
2. **This is BUG #2 above biting for real.** I filed "no progress output, so slow is
   indistinguishable from hung" as cosmetic and deferred it. It was not cosmetic: with no output
   I could not tell a slow job from a wedged one, and the only reason I knew it was alive was
   inspecting its resident memory from PowerShell.

**Repaired:** contract selection is now keyed and joined once per symbol-year instead of masked
per contract (`_contract_rows`), and `freeze_book` takes `progress=True`. Each contract keeps its
**own** date window rather than a pooled min/max — a pooled window would freeze rows the book
never read, which is safe for replay but would misreport what the book consumed, and that number
is the entire basis of the cost measurement above. Two tests pin the window behaviour and the
no-match case.

**The optimisation was verified to be behaviour-preserving on the real book, not just on
fixtures:** re-freezing R2 through the new path gives **2,870,811 rows against the banked
2,870,811**, content-identical after sorting. 707s vs 1,153s — a 1.6× win here, because for a
book this size *frame loading* dominates; the win scales with contract count, which is where the
control seeds were dying.

**A CORRECTION TO MY OWN REASONING, recorded because it nearly became documentation.** An interim
version of the rewrite collapsed a contract's multiple date windows into one `[min, max]` span,
and the resulting freeze was **14,231 bytes larger** than the banked one. I read that as proof of
exactly the over-inclusion I had warned against, and started writing it into the code comment as
a measured fact. **It was not true.** Checked properly, the two row sets are *identical* — gzip
was simply compressing a different row ORDER. The per-window predicate is kept regardless,
because it matches the original loop *by construction* rather than by luck of this book's
contract mix, and a test now pins the disjoint-window case that actually distinguishes them. A
byte-size difference is not a row-set difference, and I should have checked before concluding.

### The controls freeze took three attempts, and the third worked

| attempt | outcome |
|---|---|
| 1 — whole job, per-contract scan | killed by the environment at ~45 min, **0 rows written** |
| 2 — whole job, vectorised | killed by the environment at 600/1,558 symbol-years |
| 3 — **six ticker shards, foreground** | **completed**, 129-152s per shard, ~13 min total |

**The operational finding worth carrying: this environment stops long-running background jobs,
and both failures were that rather than anything wrong with the data.** Sharding by ticker is
sound here because `freeze_book`'s work is keyed by `(ticker, year)` — no shard can affect
another's rows — so the shards are independent and their union is exactly the whole freeze.
`bank_controls_shard.py combine` concatenates, de-duplicates, writes the manifest and deletes the
shard files.

**Result: 21,877,728 rows, 168,934,527 bytes (168.9 MB).** Note it is **7.6× the R2 book's row
count** off 7.7× the trades — the controls are random-entry, so their alert dates are spread far
more widely across the store than the real book's clustered ones.

**Total freeze footprint on disk: 23.3 MB + 168.9 MB = 192.2 MB, against a 26.98 GB store —
0.71%.** The whole defended set costs under three quarters of one percent of what it defends.

---

# 2026-08-08 — O1 + O23: do the exits carry anything, tested against random entries?

**Register:** `PREREG_o1_o23_exits.md`, committed at **`dc2c486` before any policy was scored**.
**Artifacts:** `data/options_exitlab/EXITLAB_FROZEN_2026-08-08.json`,
`data/options_exitlab/O23_UNDERLYING_2026-08-08.json`.
**Verdicts: O1 REJECTED. O23 NULL (set-dependent).**

**The routed hygiene item was already done.** Session 12 asked me to escape the unescaped `|` in
my O16 row. It was repaired last cycle at `fd36e25` (`|Spearman(...)|` → `abs(Spearman(...))`);
measured today the parser reads **`rows_malformed: []`** across all 74 rows. No commit was needed
and none was made — a no-op commit would have looked like work.

---

## 1. THE FREEZE HELD, AND THAT IS THE FIRST THING TO SAY

This is the **first research to run entirely off the chain freeze**, and the register made that
falsifiable rather than decorative: `FrozenChains` has **no fallback to the live store**, so a gap
surfaces as a missing path instead of a silent live read.

| gate | signal (R2 book) | random (5 control seeds) |
|---|---|---|
| **G0a** contract histories served from the frozen copy | **3,885 / 3,885** | **29,785 / 29,785** |
| freeze fingerprints re-verified | 1,429 / 1,429 clean | 1,558 / 1,558 clean |
| **G0b** shipped policy vs the banked book — parity mode | **99.820%** | **99.865%** |
| **G0b** under honest settlement | **100.000% (3,885/3,885)** | — |

The 7 residuals under parity mode are **exactly the 7 `settled_at_intrinsic` trades**, which is
the case the parity mode is *defined* to differ on. Nothing is unexplained.

**And the replay reproduces R2's published headline independently, having rebuilt every path from
frozen bytes rather than copying a number:**

* R2 published **real +3.41%/trade vs control +10.06%** → replay **+3.41% vs +10.06%**.
* R2 published a control per-seed range of **+6.46% to +15.34%** → replay **+6.46% to +15.34%**.

That is the strongest evidence to date that the freeze is sufficient, and it is worth more than
the freeze's own self-check because the target was a number the freeze did not write.

---

## 2. O1 — THE EXIT SWEEP. VERDICT: **REJECTED**

21 policies × {3,885 alert entries, 29,785 random entries over five pooled seeds}, gate X1–X5
imported unamended, date-block (calendar-month) bootstrap at 2,000 draws seed 0, **paired
name-year sign test carrying the verdict** per the standing R2 rule.

**No policy clears the gate. PBO 0.000 on both entry sets; the held-out chooser survives in both
directions on both sets.**

### 2.1 The one policy that clears the expectancy bar fails the statistic that decides

`tp100_only` (take-profit at +100%, **no stop, no time stop**) is the only policy to clear the
pre-committed 10pp signal bar, and on pooled expectancy it looks like the answer:

| | shipped | tp100_only |
|---|---|---|
| expectancy / trade (signal) | +3.41% | **+14.19%** (+10.78pp) |
| expectancy / trade (random) | +10.06% | **+27.92%** (+17.86pp) |
| clustered CI95 on the signal gain | — | **[+6.26pp, +15.29pp]**, excludes zero |
| both halves positive, both sets | — | yes |
| chosen by the held-out selector | — | in **all four** directions |

**And it loses in a majority of name-year cells on the alert book.** Paired sign test:
**z −5.76**, winning **41.7% of 1,217 decided cells**, **median cell −5.79pp**. The mechanism is
visible and it is not subtle:

| | shipped | tp100_only |
|---|---|---|
| share of trades that are **total losses** | **1.39%** | **46.87%** |
| median trade | −52.2% | −37.9% |
| mean holding period | 14.5 d | **42.6 d** |
| tail share of gross winnings | 86.8% | 92.8% |

Removing the stop converts nearly half the book into zeros and pays for it with a fatter tail.
The mean rises; the typical name-year gets worse. **The pre-registered direction rule caught it:
`analyse` assigns p = 1.0 to any policy whose sign z is negative, so a large mean carried by a few
trades can never enter the FDR pool as a discovery.** That guard was written before this run for
exactly this failure mode, and this is the first time it has fired on a policy that would
otherwise have been adopted.

**On the random book the same rule genuinely works** — 64.5% of decided cells, z +10.55, median
+11.13pp, and stable across every seed (+15.9pp to +22.2pp). By the verdict-carrying statistic it
is **CONTROL-ONLY**, not an exit effect.

### 2.2 The structural finding: what is BROAD is SMALL, what is LARGE is NARROW

| policy | signal gain | signal sign z | signal decided-cell win | random sign z | reading |
|---|---|---|---|---|---|
| `tp100_only` | **+10.78pp** | **−5.76** | 41.7% | +10.55 | big mean, loses the cells |
| `tp150` | +3.19pp | **+7.93** | **66.2%** | **+8.09** | broad on BOTH sets, small |
| `tp200` | +3.82pp | **+4.57** | 58.8% | **+5.12** | broad on BOTH sets, small |
| `sl30` | **−3.11pp** | **+13.13** | **69.9%** | −3.94 | wins the cells, loses the mean |

`tp150` and `tp200` — simply **raising the take-profit** — are the only policies that are FDR
discoveries *and* positive on the sign test on *both* entry sets. They are real and they are
small: +3.19pp and +3.82pp against a bar of 10pp that was committed before the run. `sl30` is the
exact mirror image of `tp100_only`: it wins 69.9% of decided cells while *losing* 3.11pp of
expectancy.

**Mean and median disagree systematically on this payoff, and which exit "wins" depends entirely
on which statistic you quote.** That is the most transferable thing in this study.

### 2.3 A reporting hazard worth carrying

`paired_cells` returns `win_rate` over **all** cells and `sign_z` computed over **non-tied** cells
only. Adjacent fields, different denominators — so `tp150` reads "win_rate 0.296" beside "z
+7.93", which looks like a contradiction and is not (740 of 1,338 cells are ties, because raising
a take-profit only matters on trades that would have hit +100%). **Every win rate in this write-up
is the tie-excluded one and is labelled "decided-cell".** Quoting the raw `win_rate` next to the
sign test would publish an apparent contradiction.

### 2.4 The four-way label is asymmetric by inheritance — stated, not hidden

The register's pattern table (both / signal-only / random-only / neither) is applied to the gate's
own fields, and **X1(a) applies a 10pp bar to the signal set while X1(b) applies only > 0 to
random**. So "CONTROL-ONLY" in the raw table means *"did not clear 10pp on signal"*, **not** *"hurt
on signal"*. Recounted symmetrically: **13 of 20 policies are positive on both sets; 1 of 20
clears 10pp on both.** The asymmetry is inherited from the 2026-08-03 gate, not introduced here,
and the verdict does not turn on it — but the label would mislead anyone reading the table alone.

---

## 3. O23 — EXITS AGAINST THE UNDERLYING. VERDICT: **NULL** (set-dependent)

Policies share an identical entry and differ only in exit date, so the P&L difference is
attributable to the two exit dates alone. Regress `Δ_opt` on `Δ_und` over the same two holding
periods, restricted to trades whose exit actually differs.

| set | pairs | blocks | R² | CI95 | label |
|---|---|---|---|---|---|
| signal | 26,851 | 118 | **0.53304** | [0.48564, 0.58428] | **NULL** — point clears 0.50, lower bound does not |
| random | 210,731 | 118 | **0.55737** | [0.53112, 0.61686] | **UNDERLYING-DRIVEN** |

The register states the verdict on the signal book and **downgrades a disagreement to NULL**. That
is what is recorded. A near-miss is a NULL, not a "nearly".

**Reported rather than buried, because the NULL alone would mislead: the POOLED fit understates
the per-policy relationship.** Slopes range **6.36 to 17.45** across policies, and a pooled
regression over heterogeneous slopes loses R². Per policy on the signal book the **median R² is
about 0.70 and 17 of 20 exceed 0.50**, from 0.4180 (`tp100_only`) to 0.7542 (`dte21`). The policy
with the largest expectancy gain is the **least** explained by the underlying — which is what
holding an all-or-nothing payoff to expiry does to a linear fit.

### 3.1 The Greek attribution agrees by a completely different route

Secondary, **carries no verdict**. Of the total *absolute* mark movement between the two exit
dates (23,983 pairs, 2,868 skipped, r = 3%):

| term | share of absolute movement | mean **signed** contribution |
|---|---|---|
| **delta** | **50.70%** | **+0.4617** |
| gamma | 15.57% | **+0.8528** |
| theta | 14.07% | **−0.7708** |
| vega | 13.25% | +0.2376 |
| residual (linearisation) | 6.41% | −0.2026 |

Delta alone lands on the **same ~50%** the regression found, by an independent method. Delta +
gamma is 66.3%.

**The signed column is the sentence worth keeping: gamma +0.85 and theta −0.77 nearly cancel,
leaving delta +0.46.** Holding a long call longer buys convexity and pays for it in decay at
almost the same rate; what survives is the direction of the stock.

---

## 4. FOR DON — one plain paragraph, and it answers the 37/63 question

You asked what the winners share and what tricks us in the losers. On the current book you win on
**35.3% of trades** and lose on 64.7%, and **86.8% of everything you make comes from trades that
gained 100% or more** — so the book is already a lottery-ticket book, and that is by design, not a
fault. We tested 21 different ways of getting out, against your real alerts and against 29,785
random entries picked on the same stocks and the same days. **Nothing beat the exit you already
have.** The one rule that made the average much better — never stop out, just wait for a double —
turns out to make *most* individual stock-years **worse**: it wins on 42% of them and turns 47% of
all trades into total write-offs, versus 1% today. It works by making the lottery more extreme,
not by picking better. Two small changes look genuinely real on both your alerts and random
entries — taking profit at +150% or +200% instead of +100% — but they are worth about 3 points a
trade, and we agreed in writing beforehand not to change anything for less than 10. And the deeper
answer to "what tricks us": **about half of what any exit rule gains or loses is just the stock
moving**, and of the option-specific part, the convexity you gain by holding longer is almost
exactly cancelled by the time decay you pay for it. The exit is not where the money is. **The entry
is still dead (that has not changed), and the exit is not hiding an edge behind it.**

---

## 5. WHAT I DID NOT DO

* **Did not re-open the entry signal.** R2 stands and was not re-tested.
* **Did not amend the 21 policies**, add one, or retune one. They are imported from the
  2026-08-03 register unamended.
* **Did not cite the 2026-08-03 exit lab's REJECT as corroboration.** It ran on the
  pre-correction book, with ~2 control draws, through the pre-B2 filter repaired below. Its
  agreement with this run is not independent and is not claimed as support.
* **Did not run a run-scope freeze.** The freeze is trade scope, so this study can replay a
  book's exits but cannot re-derive *which alerts fire*. O1 is an exit study and does not need
  that; no conclusion here may be extended to entry selection.
* **Did not freeze the underlying bars store.** O23's headline depends on it. The files consumed
  are fingerprinted per run (`stamp_bars`), which makes the gap auditable but does not close it.
* **Did not act on `tp150`/`tp200`.** They are the nearest thing to a positive result and they
  are below a bar committed before the run. Promoting them now would be selecting on the results.
* **Did not test exits on the equity book or on spreads.** Long calls only.

## 6. EXPECTATIONS, SCORED

* **O1: I wrote REJECT at 70/30 before the run. Correct.**
* **O23: I wrote UNDERLYING-DRIVEN at 60/40. The verdict is NULL** — both point estimates clear
  0.50 and the random book clears outright, but the signal book's interval straddles the bar. Call
  it wrong: the register asks for a label and the label is NULL.

One right, one wrong. The standing rule holds — do not reason about the direction of an effect in
this project, measure it.

---

## BUGS FOUND

**1. `options_exitlab.capture_path` was never moved to audit B2's exit tolerance. (REPAIRED,
`4170ad9`.)** B2 moved `options_backtest.simulate_trade:367` to `F.exit_reject_reason`; the exit
lab kept the strict `quote_reject_reason(check_liquidity=False)`, so **wide-spread and
thin-premium days were deleted from every trade's exit path.** That is precisely the failure B2's
own docstring describes: a bad price is not an absent one, and a loser that decays through the
−50% stop on a wide-quote day is never stopped. Nothing caught it because nothing had ever
replayed a *post*-B2 book through the exit lab.

*Localised before it was theorised.* The drift hypothesis was tested **first and refuted** —
untouched symbol-years matched at 86.5% against re-mined ones at 88.7%, nothing like O16's
100%/30.5% signature — so the store was exonerated. Entry fills matched 3,885/3,885 and
`held_days(replay) − held_days(book)` was **never negative**, which put it in the exit day-walk
and nowhere else. One ABBV contract kept **7 of its 34** quote days. Effect: **86.950% → 99.820%**
(100.000% honest) on one line. Three tests fail on the old line; the key one returns `time_stop`
where the fix returns `stop`.

**Consequence beyond this study: the 2026-08-03 exit lab scored all 21 policies on paths with days
silently removed, and the bias is policy-dependent because it lands hardest on stop-based rules.**
That is an independent reason its verdict is not transferable, found by measurement.

**2. `paired_cells` reports `win_rate` and `sign_z` on different denominators.** Not a defect —
the sign test correctly excludes ties — but the two sit adjacent in one dict and invite publishing
"wins 29.6% of cells, z +7.93". Handled in §2.3; flagged because it is a live trap for anyone
quoting that dict.

**3. Three defects in my own new code, all found by running it.** Recorded because they were live
long enough to have produced numbers: **(a)** the frozen frame keeps `strike` as **float32**, and
merging on the raw float64 cast silently dropped 14 of 3,885 contracts (`140.0` →
`140.00000762939453`); **(b)** `FrozenChains` built one DataFrame object per contract, which on an
unfiltered freeze is 2.09M objects — measured at ~12 GB against 6.6 GB free, so it thrashed rather
than failed; **(c)** `greek_attribution` assumed textbook units, but `options_greeks` returns vega
per **1.00 of vol** and theta per **year**, and `implied_vol` returns an **(iv, reason) pair**. Two
of those three would have silently rescaled a term and only the third crashed — which is the only
reason the other two were caught. Units are now pinned against finite differences of `bs_price`
rather than against the docstring.

**4. Two of my own statistics would not have finished as written.** The register's 2,000-draw
clustered intervals are ~4.8 billion list operations for the policy diffs, and a re-fit over
~400k pairs per draw for the R². Both statistics depend on the data only through **additive
per-block sums**, so both were rewritten to be O(blocks) per draw. **Pinned as exact, not merely
faster:** point estimate and both interval endpoints match `options_stats.date_block_diff` to 12
decimal places at the same seed and draw count.

**5. Per-seed attribution cannot be keyed by trade fields.** Two seeds that draw the same ticker
on the same day select the same contract by the same rule, so even
`(ticker, date, strike, expiry)` collides — a key-based map put 6,820 trades in seed0 against a
true 6,032. Recomputed by index range over the seed-ordered pooled book, which is exact because
every path produced exactly one row per policy (625,485 = 21 × 29,785). Seed counts now reconcile
to the manifest exactly.

---

## Trial accounting

**Options 169 → 192** (O1 `n=21`, O23 `n=2`), charged in full: the 2026-08-03 verdict was read
before this run, so it was not blind (O16-REFROZEN precedent). **Equity `N` unchanged at 129**, so
**no equity claim moves** — Deflated Sharpe stays 0.8556, √(2·ln 129) stays 3.1176. Infra 4,
total 325, `rows_malformed: []`.

**Reproduce:** `python -m tests.test_options_exitreplay` for the instrument;
the runners live in the session's job directory and read only
`data/options_freeze/{R2_CORRECTED,R2_CONTROLS}_2026-08-08/` plus `data/bulk/prepared/bars/`.

---

# V5 — Measured slippage vs modelled costs (2026-08-09, options bot)

**Register:** `VALQUO_EXTENSIONS.md` V5. **Pre-registration:** `PREREG_v5_slippage.md`, committed
at `c06ac55` **before `scripts/slippage_report.py` existed and before any fill was read.**
**Artifact:** `data/options_slippage/V5_SLIPPAGE_2026-08-09.json`. **Tests:**
`tests/test_slippage_report.py`, 52. **Reproduce:**
`python scripts/slippage_report.py --from-export data_export/paper_track_history.json`.

## 0 · The one-paragraph version

The instrument is built, pre-registered, tested and landed. **Its headline verdict is
INSUFFICIENT and that is the pre-registered outcome, not a shortfall:** the paper book holds
**three entry fills and zero exits**, so the exit half-spread — the only measure directly
comparable to the modelled cost — has n = 0. The register's expectation was INSUFFICIENT at
90/10 and it was right. What is *not* nothing is what those three rows already say: the
sandbox handed the book up to **20.2% of price improvement** on a limit order placed at the ask,
and reading them turned up **two defects in shipped code**, one of which means two of the three
live positions are running exit levels no backtest describes.

## 1 · The modelled bar is measured, and the brief's number is the wrong currency

The register fixes the bar as literals before anything is measured, from
`data/options_universe/state_r2_corrected.pkl` — the authoritative R2-corrected book, with
`entry_spread_pct` present on **3,885 of 3,885 trades (100.0%)**. Half-spread paid at entry is
`entry_spread_pct / 2`, because `spread_pct = (ask − bid) / mid` and the fill is at the ask.

| modelled quantity | value |
|---|---|
| entry half-spread, **mean** | **410.0 bps of premium** |
| entry half-spread, median | 333.3 bps |
| p10 / p25 / p75 / p90 | 131.8 / 198.0 / 550.0 / 837.0 bps |
| max | 1250.0 bps — this is `MAX_SPREAD_PCT` 0.25 ÷ 2, so the cap binds |
| median entry premium | $2.58 |
| commission | $1.30 round trip = **50.4 bps** of that premium |

**THE BAR WAS CROSS-CHECKED AGAINST A SECOND ARTIFACT AND THE TWO AGREE TO ZERO.** O1's
`data/options_exitlab/paths.pkl` stores raw `entry_bid` / `entry_ask` per trade, an independent
route to the same quantity. On the **1,099 trades that match** between the two files, the direct
`(ask − mid) / mid` and the book's `entry_spread_pct / 2` disagree by **0.000000 bps at the
maximum**. The distribution is also bounded exactly where it should be — the book's maximum is
1250.0 bps, i.e. `MAX_SPREAD_PCT` 0.25 ÷ 2, which is the entry gate binding.
**One thing worth recording so nobody re-derives a different bar:** the same statistic computed
over `paths.pkl`'s own 3,119 rows is **323.0 bps**, not 410.0, and that is a SAMPLE difference,
not a disagreement — it is a partial rebuild, and restricting the book to its ticker set still
gives 409.0, so the gap is which TRADES survived the path rebuild rather than which names. **The
authoritative 3,885-trade book is the bar. Do not quote 323.**

**V5's brief says to compare against "the modelled 33.4bps" and that would have been a category
error of roughly an order of magnitude.** 33.4 bps one-way is audit **B11**'s measured cost on
the *fundamental panel* — basis points of **stock notional**. This book pays ~410 bps of
**premium** per side. 410 / 33.4 ≈ **12×**, and they are not the same denominator. The report
prints that sentence on every run rather than quietly substituting the right number, because the
33.4 figure is already circulating and someone will try to apply it here again.

## 2 · Why a limit-at-the-touch book needs four measures and not one

The obvious statistic — did the fill beat the order's limit — is **worthless here, and the
register says so in advance rather than after seeing the answer.** `paper_track` submits a LIMIT
buy at the ask and a LIMIT sell at the bid, so a fill can never be worse than its limit. Lead
with that and you publish "0 bps of slippage" forever: not a measurement, a restatement of the
order type.

| | measure | status today |
|---|---|---|
| **M3** | **exit half-spread vs the mid — THE HEADLINE**, the only measure comparable to 410.0 bps | **n = 0 → INSUFFICIENT** |
| M2 | fill vs the touch, reconstructed offline. Structurally bounded ≤ 0; never a headline | n = 3, not quotable |
| M4 | the **fill funnel** — the cost M1/M2 structurally cannot see | 3 rows, 3 filled, 100.0% |
| M5 | alert-ask → fill drift. **Reported and labelled NOT SLIPPAGE** (different timestamps) | n = 3, not quotable |

**The minimum sample is a refusal, not a warning.** Below 30 filled legs the script computes no
mean, no CI and no verdict, prints the raw values, and says `NOT QUOTABLE (n=k < 30)`. Three
tests pin that a mean cannot appear at n = 29 and does appear at n = 30.

**Inference, when there is ever enough of it:** percentile bootstrap of the mean, 2,000 draws,
seed 0, **resampling CALENDAR WEEKS, not legs.** One alert engine fires several names on a day
and names repeat; audit **R3** found every earlier options interval was optimistically narrow for
exactly that reason. A test pins that clustering *widens* the interval on the same 120 values
when weeks disagree — if a later edit silently drops the blocks, that test fails.

## 3 · What three fills already show, at n = 3 and quoted as raw values

The paper book, from the git-committed Render backup (`generated_at 2026-08-09T07:15:04`):

| | alert ask | submit ask | fill | fill vs its own limit |
|---|---|---|---|---|
| TGT 260918C160 | 4.55 | 4.45 | **3.55** | **−2022.5 bps (−20.2%)** |
| MET 261016C100 | 4.90 | 4.90 | **4.60** | **−612.2 bps (−6.1%)** |
| ETN 261016C500 | 16.10 | 16.10 | **16.10** | **0.0 bps** |

The submit ask is not stored; it is recovered by inverting `_place_entry`
(`target_premium / (1 + target_pct)`). **That reconstruction is corroborated independently:** the
*stop* column, a different multiplier, gives the same submit ask to four decimals on all three
rows.

> **CORRECTED WITHIN THIS SESSION, BEFORE LANDING. My first reading of these three numbers was
> "the sandbox granted up to 20.2% price improvement", i.e. I credited the fill engine. THE
> TIMESTAMPS REFUTE THAT AND THE REAL CAUSE IS WORSE.** Every order waits **12.8 to 15.9 hours**
> between the limit being placed and the fill:
>
> | | limit placed | filled (UTC) | elapsed |
> |---|---|---|---|
> | TGT | 2026-08-03T21:51:47 | 2026-08-04T13:46:15Z | **15.9 h — next session** |
> | MET | 2026-08-07T00:58:52 | 2026-08-07T13:47:15Z | 12.8 h |
> | ETN | 2026-08-07T00:58:53 | 2026-08-07T13:46:09Z | 12.8 h |
>
> All three fill at **13:46–13:47 UTC = 09:46–09:47 ET, the opening minutes.** The cause is
> structural and scheduled: `auto-scan.yml` runs the paper cycle at **20:47 / 21:47 UTC =
> 4:47pm ET, AFTER THE CLOSE**. So the entry limit is set from a **post-close quote**, the order
> is a `day` order, and it fills at the **next open**.

**So "fill vs limit" on this book is an overnight gap, not execution quality**, and the report
now prints the elapsed time beside it (`diagnostic_submit_to_fill`) so nobody else makes the
mistake I did. Two consequences, and both are real:

* **The paper book's entry basis is not the backtest's.** The backtest fills at the ask quoted on
  the alert day (`option_alerts.entry_premium`: TGT 4.55). The paper book paid **3.55** — 22%
  better, for a reason the backtest does not model. On entry that flatters the forward track
  relative to the thing it is meant to test.
* **It makes BUG 1 below systematic rather than occasional.** The target and stop are anchored to
  a quote from a *different session* than the fill, so they will be wrong whenever the option
  gaps — which is 2 of 3 so far.

Quote it with its n: **three fills is three fills.**

## 4 · BUGS FOUND — two in shipped code, reported not repaired

V5 is scoped **NEW FILES ONLY**, so both are routed with the exact fix rather than made here.

**BUG 1 — the live exit levels are not the backtested ones. 2 of 3 open positions are off spec.**
`paper_track._place_entry` derives `target_premium` and `stop_premium` from the price the order
was **submitted** at; `mark_open` then overwrites `entry_premium` with the broker's actual fill
and **never recomputes either level.**

| | fill | live target | intended | live stop | intended |
|---|---|---|---|---|---|
| TGT | 3.55 | **+150.7%** | +100% | **−37.3%** | −50% |
| MET | 4.60 | **+113.0%** | +100% | **−46.7%** | −50% |
| ETN | 16.10 | +100.0% | +100% | −50.0% | −50% |

ETN is on spec only because its fill equalled its limit. **Both drifts run against the paper
book** — a farther target is harder to reach, a tighter stop is easier to hit — so this is not
the flattering direction; but the *comparability* claim breaks either way, and comparability is
the entire point of the track. Same family as audit **B5c**, which repaired the *resume* branch's
missing levels; the fresh path still anchors them to the pre-fill price.
**And per §3 it is systematic, not occasional:** the limit is set after the close and the fill
happens at the next open, so the two prices routinely differ.
**Fix:** recompute both levels from the fill in `mark_open`'s `status == "filled"` branch.

**BUG 2 — the paper track buys names the alert's own sizing refused.** Alert 3 (ETN) carries
`"sizing": {"contracts": 0, "skip": true, "reason": "one contract costs $1,610, above the $1,000
budget - cannot be sized correctly"}`. The paper track bought one contract anyway:
`submit_new_alerts` takes its size from `cfg.paper_contracts_per_trade` and `_eligible` tests
only the contract, the expiry and the alert's age — `features.sizing` is never read.
**It is the largest position in the book.** **Fix:** honour `features.sizing.skip` in
`_eligible`, with the reason recorded on the skipped row.

**GAP 3 (routed, not a bug) — the ENTRY half-spread is not measurable at all.**
`paper_option_orders` stores no bid, ask or mid at submit. The **ask** is recoverable; the
**mid** is not, by any route, and a half-spread needs a mid. So M3 covers the **exit leg only**,
and the report names which leg every number belongs to. **Fix:** two columns, `entry_bid` and
`entry_ask`, written in `_place_entry` beside the existing target/stop.

## 5 · Two corrections to the project's own record

**`paper_option_orders` is no longer empty, and `CLAUDE.md` still says it is.** That file's
roadmap-#12 bullet reads *"`paper_option_orders`, `paper_index_holdings` and `paper_index_track`
hold **0 rows each** — the engine has never been fed."* Measured today from the committed
backup: **3 paper orders, 10 index holdings, 4 index-series rows.** The engine has been fed since
2026-08-04. The bullet was true when written and is stale now.

**Every screener store off Render holds zero paper rows, and the backup is the read path.** The
track runs on Render's persistent disk behind `/admin/run-paper-track`; both local `screener.db`
copies read 0. What *does* reach the repository is `.github/workflows/track-backup.yml`, which
curls `/admin/export-track` and commits `data_export/paper_track_history.json` — and
`track_export.payload` carries `paper_option_orders` verbatim. **The backup written to protect
the record doubles as the only reachable way to measure it**, so `--from-export` is a first-class
input, not a convenience. Without it this instrument would be ornamental.

## 6 · What I did NOT do

* **Did not repair either bug.** V5 is new-files-only; both are in `valuation/edge/paper_track.py`,
  which the pipeline-builder lane owns. Routed with fixes named.
* **Did not add the two entry-quote columns**, for the same reason — and the report says
  `ROUTED, NOT MADE` in its own output so a reader cannot mistake the gap for an oversight.
* **Did not quote any aggregate.** n = 3 against a pre-registered minimum of 30. The mean of
  those three numbers is not in this write-up, in the artifact, or in the log row.
* **Did not lower the modelled cost.** The register forbids acting on DIVERGENT-CHEAPER on its
  own, because sandbox optimism already points that way.
* **Did not touch the entry signal.** R2 stands: real +3.41%/trade vs a random-entry control's
  +10.06%, sign-test z −4.903. A cost measurement cannot revive an entry signal.
* **Did not feed S14's no-trade band or the capacity number.** V5's brief asks for that, and it
  is not possible: both are **equity** constructs, `seed_book(place_equity=False)` is the default
  so **no equity fills exist**, and option-leg slippage cannot feed them. Stated as a limitation
  in the report's own output rather than worked around.

## 7 · Expectations, scored

* **"INSUFFICIENT, at 90/10" — RIGHT.** n = 0 on the headline.
* The conditional call (DIVERGENT-CHEAPER at 60/40) is **not yet scorable** — no exits. The
  entry-side evidence at n = 3 leans hard that way, but that is a different measure and is not
  claimed as a hit.

## 8 · Trial accounting

Instrumentation searches nothing and selects nothing, so it is charged to **infra** at `n = 1` on
the HACFLOOR / CHAINFREEZE precedent. **Options `N` stays 192 and equity `N` stays 130** — no
DSR-gated claim moves; Deflated Sharpe stays 0.8547 at 130. Infra 4 → **5**, total 326 → **327**,
63 rows counted, 21 `FIXED` not counted, `rows_malformed: []`.

## 9 · Recommended next step

**Route BUG 1 and BUG 2 to whoever owns `paper_track.py`, before the exits start landing.** BUG 1
in particular corrupts the comparison the whole forward track exists to make, and every day it
stays open is another position entered under levels no backtest describes. The instrument itself
needs nothing further until roughly 30 exits exist — on a three-position book at the current
alert rate, that is a long way off, which is itself worth knowing.

---

# LA15 — the test suite writes into the real databases (2026-08-10)

**Item:** `VALQUO_LIVE_AUDIT.md` LA15, severity LOW, class `test-mutates-production-state`.
**Scope:** `tests/**` only. No production module was edited.
**Files:** `tests/state_isolation.py` (new), `tests/test_state_isolation.py` (new, 29 tests),
plus a two-line guard import in eight existing suites.

## 1. What the audit said, and what was actually there

The audit named one row: `tests/test_saas.py:200-205` POSTs `/admin/ingest-snapshot` with
`scan_date: "2099-01-01"` against a `Store()` that resolves to the repository's real
`data/screener.db`, and `latest_scan_date()` orders `DESC`, so the fixture outranks every real
scan forever.

Measured on this checkout, **one run of that one suite left six rows across five tables plus a
meta key**:

| table | row |
|---|---|
| `meta` | `hot_processed_2099-01-01` |
| `scans` | `2099-01-01`, provider `ci` |
| `snapshot_rows` | `TESTX` @ `2099-01-01`, hot_score 91.0 |
| `track_picks` | `hot10` / `2099-01-01` / `TESTX` |
| `positions` | an **OPEN** `hot10` paper position in `TESTX` at $10.00 |
| `alerts_sent` | `__HOTDIGEST__`, `alert_date` = **the real calendar day the test ran** |

The last row is the one that is not cosmetic. `notify.post_hot_digest` returns early when
`store.alerted_today("__HOTDIGEST__")`, and `mark_alerted` stamps *today*, not the scan date —
so **running the suite on a box with a Discord webhook configured suppresses that day's real
hot digest.** A test may not decide whether the product notifies its users.

## 2. The primary checkout is polluted right now (read-only check, nothing was changed)

| | measured |
|---|---|
| `data/screener.db` latest scan | **`2099-01-01`, and it is the ONLY scan_date present** |
| open positions | 1 — the `TESTX` fixture |
| `data/app.db` user accounts | **34**, all created by test runs |
| `data/archive/scans/` | 3 days, **all** `provider: "synthetic (offline test)"` |

Every scan-derived surface on Don's local app — `/api/hotstocks`, `/api/valquo-index`,
`/api/whatdo`, the hero — is serving the fixture. The audit predicted this; it is confirmed
live rather than inferred. **Nothing was deleted: that is Don's call, and the commands are in
§8.**

## 3. The sweep — measured, not read

`data/`, `data_export/`, every repo-root file and `git status --porcelain` were fingerprinted
(size + mtime + sha1) around a subprocess run of **each of the 37 suites then present**, before
and after.

**Four suites mutate real state, three of which the audit did not name:**

| suite | what it wrote |
|---|---|
| `test_saas.py` | `data/screener.db` **and** `data/app.db` |
| `test_security.py` | `data/app.db` |
| `test_screener.py` | `data/archive/scans/<today>.json.gz` |
| `test_private.py` | opened the real `screener.db` (its `-wal`/`-shm` were checkpointed away) |

One reported mutation was **a false positive and is discounted**: `test_theme_health.py`'s
`__git_status__` hit is the guard module I created while the sweep was still running. Recorded
here rather than quietly dropped.

Three further suites **read** real state without writing it — `create_saas_app` opens
`data/app.db` — and so their results depend on those 34 accounts: `test_public.py`,
`test_research_page.py`, `test_score_confidence.py`. `test_paper_track.py` reads
`data/valquo_track.json`. All are covered.

## 4. Four escapes, enumerated

```
create_saas_app(...)   -> UserStore(cfg.database_url)      -> data/app.db
Store() / UserStore()  -> no path                          -> data/screener.db, data/app.db
run_scan(..., save)    -> screen.py -> archive_scan()      -> data/archive   (RELATIVE root)
live_hero(...)         -> index_track.default_paths()      -> data/valquo_track.json + .csv
```

The third is the interesting one. `test_screener.py` passes a **temp store** — the author did
isolate the database — but `screen.py:336` calls `archive_scan(rows, scan_date, provider.name)`
with no root, and `archive.DEFAULT_ROOT` is the *relative* path `data/archive`, resolved against
the cwd and bound as a default argument at def time. A relative default root is invisible from
the call site, which is why isolating the store was not enough. **This is the same class as the
miner's `data/options` root already pinned in `tests/test_edge.py:4567`.**

## 5. THE FINDING THAT LEAVES THIS LANE: the local scan archive is 100% test output, and it
   grows by one fabricated day per day

Every archived scan day on this checkout — **5 of 5**, and **3 of 3** in the primary checkout —
reads `provider: "synthetic (offline test)"` with 100 `SYN####` tickers. One file per calendar
day the suite was run:

```
2026-08-06  synthetic (offline test)  100 rows  SYN0706
2026-08-07  synthetic (offline test)  100 rows  SYN0410
2026-08-08  synthetic (offline test)  100 rows  SYN0807
2026-08-09  synthetic (offline test)  100 rows  SYN0612
2026-08-10  synthetic (offline test)  100 rows  SYN0513
```

`scripts/theme_health.py` — the **V2** instrument — reads exactly `data/archive/scans/`. V2
reported that "every archived scan day is synthetic and the store's one row is a 2099 test
fixture" and correctly called the theme-health meter NOT-QUOTABLE. **Both halves of that
sentence are this audit item**: the archive days come from `test_screener.py`, the 2099 row from
`test_saas.py`. V2 diagnosed the symptom; this is the mechanism.

The dangerous property is that it is **self-refreshing**. The directory is not empty and not
obviously broken — it accrues one more plausible-looking day every day anyone runs the tests, so
it reads as accumulating history. → **V2's lane (greeks agent): the archive cannot be treated as
a partially-real series with synthetic gaps. On any developer box it is synthetic in full.**

## 6. The other finding: two of the project's strongest guards fail on a developer box, with
   messages that assert the opposite of what happened

`HANDOFF_STATUS` has carried "`test_paper_track` 37/40 locally, 40/40 in CI — don't chase it".
It was worth chasing. Copying the primary checkout's real `valquo_track.json` +
`valquo_track_history.csv` into this worktree and running the **pre-fix** suite from `HEAD`:

* **pre-fix: 65/70.** Fixed suite, same files present: **70/70.**
* The five failures are `test_hero_never_raises_and_never_takes_the_page_down`,
  `test_hero_stays_hidden_until_the_track_actually_reports`,
  `test_hero_will_not_render_the_sandbox_book_as_the_index`,
  `test_no_outbound_surface_may_quote_the_sandbox_engine_as_the_index`,
  `test_recap_will_not_quote_a_hit_rate_as_a_rate_below_the_evidence_floor`.

**Read at face value, two of those say the B7 sandbox/Index split has regressed. It has not.**
`test_hero_will_not_render_the_sandbox_book_as_the_index` fails with

> the hero rendered the Tradier sandbox book as the Valquo Index: `{'available': True,
> 'source': 'index-track', 'since': '2026-07-31', 'days': 2, 'book': 'Valquo Index (top decile,
> large-cap tier, score-weighted, 8% cap)', ...}`

— the payload it prints is `source: 'index-track'`, the **contract-bound** recorder, read
correctly from the developer's own file. The hero did the right thing; the test asserted
`available is False` on the assumption that no bound track exists, which is true in CI and false
on Don's machine. Same for the outbound-surface guard, whose recap is labelled *"paper,
contract-bound Valquo Index"*. **Nobody should quote those local failures as evidence of a
sandbox leak.**

The fix does not weaken either guard: in CI there are no track files, so pointing
`default_paths()` at an empty temp directory reproduces CI behaviour exactly — the guards stay
as strong as they are in the gate, and now behave that way everywhere.

## 7. BUGS FOUND

**B-LA15.1 — `valuation/edge/archive.py:35`: the archive root is relative, and bound at def
time.** `DEFAULT_ROOT = os.path.join("data", "archive")` is a relative path used as a default
argument, so (a) it resolves against whatever the cwd happens to be, and (b) reassigning the
module constant does not change it. `valuation/screener/screen.py:336` calls
`archive_scan(rows, scan_date, provider.name)` with no root, so **any** caller anywhere writes
into `<cwd>/data/archive` — which is how a suite that had correctly passed a temp store still
wrote a real archive day. Same class as the miner's `data/options` root already pinned in
`tests/test_edge.py:4567`. **NOT FIXED — LA15's scope is `tests/**`.** → screener/engine lane:
resolve against the repo root or require an explicit root, and pin it.

**B-LA15.2 — `valuation/saas/notify.py:187,190`: the hot digest is deduped on the wall-clock
day, but it is a digest *for* `scan_date`.** `alerted_today("__HOTDIGEST__")` keys on today
while `mark_alerted("__HOTDIGEST__", scan_date)` stores `alert_date = today` and
`run_time = scan_date`. The docstring says "at most once per day", so the wall-clock key is
deliberate and this is **behaviour, not a verdict** — but two consequences follow that are worth
someone's attention. First, it is the mechanism by which a test run suppressed a real digest.
Second, `/admin/ingest-snapshot`'s own `already` guard is keyed on `scan_date`, so a *second,
different* `scan_date` ingested on the same calendar day — exactly the backup-cron case the
route's comment describes, since GitHub drops scheduled runs — passes that guard, reaches
`post_hot_digest`, and is silently not posted. → app lane, unverified against production
behaviour.

**B-LA15.3 — `tests/test_saas.py:2` claimed something untrue.** The module docstring has read
"offline, deterministic — temp DB, no network" throughout the period it was writing to the real
`data/screener.db`. Fixed as a side effect of this item; noted because a docstring that asserts
the property being violated is worse than none.

**B-LA15.4 — a defect in the guard itself, found and fixed before pushing.** The first version
of `_isolate_user_store` wrapped `UserStore.__init__` as `guarded_init(self, url=None, ...)`.
Two faults, both silent: the real signature's parameter is named **`database_url`**, so
`UserStore(database_url=...)` would have landed in `**kwargs` and never been checked; and the
real signature's default is **`"sqlite:///data/app.db"` — the real accounts DB** — so a bare
`UserStore()` would have been passed `None` and died with a confusing `TypeError` instead of the
guard's own refusal. Now bound off `inspect.signature(real_init)` and pinned by two tests
(`test_a_bare_user_store_raises_rather_than_opening_its_real_default`,
`test_the_keyword_spelling_cannot_slip_past`), both of which the broken version fails. Recorded
because a guard with a hole in it is worse than no guard: it reports safety it is not providing.

## 8. What was NOT done, and who owns it

1. **Nothing was deleted.** The polluted primary checkout is Don's to clear. Targeted, and only
   after the fix is merged so it does not immediately come back:
   ```sql
   -- data/screener.db
   DELETE FROM snapshot_rows WHERE scan_date LIKE '2099%';
   DELETE FROM scans         WHERE scan_date LIKE '2099%';
   DELETE FROM track_picks   WHERE run_date  LIKE '2099%';
   DELETE FROM positions     WHERE entry_date LIKE '2099%';
   DELETE FROM alerts_sent   WHERE run_time  LIKE '2099%';
   DELETE FROM meta          WHERE key LIKE '%2099%';
   ```
   plus `rm data/archive/scans/*.json.gz` (all synthetic) and, if the 34 accounts are unwanted,
   `rm data/app.db`. **Check first** — `paper_option_orders`, `paper_index_holdings` and
   `paper_index_track` are all 0 locally, so no real fill is at risk, but that is a fact about
   today, not a standing guarantee.
2. **`archive.DEFAULT_ROOT` is still relative.** The test-side guard stops the leak; the
   production smell remains and is not mine — LA15's scope is `tests/**`. → **screener/engine
   lane:** resolve it against the repo root, or require an explicit root, and pin it the way
   `test_edge.py` already pins the miner's cache root.
3. **No production module was edited at all**, including the ones the escapes run through
   (`app_saas.py`, `screen.py`, `archive.py`, `index_track.py`, `store.py`). The guard is
   entirely test-side, so nothing shipped to Render changes and the repair cannot itself be the
   cause of a production incident.
4. **The detector enumerates four escapes; it does not claim to be exhaustive.** A fifth route
   nobody has thought of would slip past the AST sweep. The runtime tripwire is the backstop for
   that case — it refuses anything resolving inside the real `data/`, whatever called it.

## 9. Verification

* `tests/test_state_isolation.py` — **29/29**.
* The eight modified suites, all green and unchanged in count: `test_saas` 30/30,
  `test_security` 22/22, `test_screener` 83/83, `test_private` 30/30, `test_public` 27/27,
  `test_research_page` 14/14, `test_score_confidence` 14/14, `test_paper_track` 70/70.
* **Re-ran the identical fingerprint sweep over all 38 suites after the fix: every suite `rc=0`,
  and the mutation list is EMPTY.** Before: 4 mutating suites. After: 0. `test_theme_health.py`
  came back clean on the re-run, which is the check that its earlier `__git_status__` hit was
  the guard module being created mid-sweep rather than a real write.
* Trial accounting: the row is a `FIXED` correctness row, so **it does not count toward `N`**.
  Measured before and after, against the shipped parser: equity **135 → 135**, options
  **192 → 192**, infra **6 → 6**, total **333 → 333**, `rows_counted` **66 → 66**. The only
  field that moves is `rows_fixed_not_counted` **25 → 26**, which is the row itself landing on
  the correct side of the counting rule. `rows_malformed: []` before and after, so the new row's
  pipes are clean — the hazard the session-12 recount exists to catch.

---

# THE PATH STUDY — stage 1 descriptive, stage 2 rejected (2026-08-10)

Pre-registered in `PREREG_path_study.md`, committed at `9d37241` **before a single table existed**
— including stage 2's whole arm set, so the arms cannot have been chosen to suit stage 1's
numbers. Reproduce with `python -m scripts.path_study --stage1`, `python -m scripts.path_arms
--run [--control]`, `python -m scripts.path_gate`.

## 0. THE CAVEAT THAT TRAVELS WITH EVERY NUMBER BELOW

**The options entry signal is dead.** R2 measured the real book at **+3.41%/trade against a
five-seed random-entry control's +10.06%** — gap −6.65pp, date-block CI95 [−11.92, −2.13],
paired sign test **z −4.903**. That stands, and this study reproduces its headline exactly as a
by-product (§2). **Nothing here is a tradeable-edge claim.** An exit rule cannot rescue an entry
that subtracts value, and O23 already measured that half of any exit's P&L difference is just the
underlying. What follows is **paper-book policy and structural knowledge**, and any sentence from
it that reads as "we found an edge" is a misquote.

## 1. What was built, and the two controls that make it believable

`data/options_exitlab/paths.pkl` — the obvious input — covers only **1,099 of the 3,885 banked
trades (28.3%)** and carries 2,020 paths the book does not. It is a different trade set. Paths
were therefore rebuilt from the frozen chains
(`R2_CORRECTED_2026-08-08/chains.pkl.gz`, 2,870,811 rows) and from `R2_CONTROLS_2026-08-08/`
(21,877,728 rows) for the five seeds.

| | signal | control (5 seeds pooled) |
|---|---|---|
| banked trades | 3,885 | 29,785 |
| **paths rebuilt** | **3,885 (100.0%)** | **29,783 (100.0%)** |

**CONTROL 1 — the replay is exact.** Scoring the shipped policy on the rebuilt paths reproduces
the banked book on **3,885 / 3,885 exit reasons AND 3,885 / 3,885 P&Ls to within 1e-9** (mean
absolute error **0.0**), and the arm's mean return is **+3.41%/trade**, which is R2's recorded
headline to the digit. Any difference an arm shows below is the arm, not the harness.
*(O1's own note records a freeze replay matching only 86.950% — that was measured under the
pre-B2 quote rule its docstring was diagnosing. Using the post-B2 rule, as the banked book did,
takes it to 100%. O1's diagnosis is corroborated.)*

**CONTROL 2 — the entry quote is derived, and the derivation is checked.** The book stores the
fill and the spread, not both sides. At aggression 1.0 a buy fills at the ask, so
`bid = ask·(2−s)/(2+s)`. Against the 1,099 trades that DO appear in O1's artifact with a true
`entry_bid`, the maximum absolute error is **0.000000000**. The 28.3% overlap is useless as a
book and is exactly the right control for that one step.

## 2. STAGE 1 — the tables. This is the direct answer to the questions asked.

### 2a. How deep do they dig? Deeper than the policy suggests.

Max adverse excursion **before the banked exit**, sell-side marks, as a fraction of premium:

| | p25 | median | p75 | mean |
|---|---|---|---|---|
| all trades | −58.4% | **−51.5%** | −26.1% | −39.7% |

| banked outcome | n | median MAE |
|---|---|---|
| target | 1,053 | **−10.0%** |
| time_stop | 527 | −32.2% |
| stop | 2,298 | −56.8% |
| expiry | 7 | −25.0% |

**80.2% of all trades touch −50% at some point in the contract's life**; 88.8% touch −25%.
Even the trades that ended at TARGET had a median drawdown of −10% and a p25 of −25.5% first.

### 2b. Do losers come back? Mostly not — and TIME LEFT is what decides it.

Measured on the **full contract life, ignoring the shipped exit** — the counterfactual the
question is actually asking. Unconditionally, **44.7%** of trades reach +100% at some point.

| first touch of | n (% of book) | back to ≥ 0 | on to +100% |
|---|---|---|---|
| −25% | 3,449 (88.8%) | 55.2% | 28.3% |
| −40% | 3,244 (83.5%) | 43.6% | 21.9% |
| −50% | 3,115 (80.2%) | **35.4%** | **17.5%** |
| −60% | 2,971 (76.5%) | 27.2% | 13.2% |

A −50% touch cuts the chance of ever making the target from **44.7% to 17.5%**. The stop is
sitting at a level that carries real information.

**And the DTE conditioning is far stronger than the level conditioning** — from a −50% touch:

| DTE remaining at the touch | n | back to ≥ 0 | on to +100% |
|---|---|---|---|
| ≤ 7 | 153 | **9.2%** | **2.0%** |
| 8–21 | 332 | 30.7% | 12.7% |
| 22–45 | 1,443 | 34.2% | 16.4% |
| > 45 | 1,187 | **41.6%** | **22.1%** |

A −50% drawdown with a week left is close to terminal; the same drawdown with two months left
recovers to breakeven **four and a half times as often**. **The single flat −50% stop is the
crudest thing in the inherited policy** — and §3 is where that intuition gets tested and does
not survive.

### 2c. How long does a winner take? Fast — so the time stop rarely binds on winners.

Of the 1,737 trades that reach +100%: median **20 calendar days**, p25 10, p75 34 — or a median
of **one third of the original DTE**. **67.6% of all targets arrive with more than half the DTE
still left.** The half-DTE time stop is therefore mostly adjudicating the undecided middle, not
cutting winners short.

### 2d. What happens after +100%? A barbell — and it vindicates closing there.

For the **1,174** trades that reached +100% with more than half their DTE still to run:

| | signal | control |
|---|---|---|
| went on to **+200%** | **67.5%** | 70.0% |
| **fell back below +100%** | **83.2%** | 82.7% |
| **fell below 0** | **58.0%** | 54.9% |
| median best price after | +273.7% | +297.9% |
| median FINAL outcome after | +62.2% | +108.0% |

Two thirds of early winners double again. **More than half of them, held on, eventually go
underwater.** The median final outcome is positive and the p25 is **−94.4%** — that is not a
distribution to hold for the mean. Closing at +100% is not leaving free money on the table; it
is swapping a barbell for a certainty.

*"Final" here means the return at the contract's **last usable quote**, which for these paths is
at or near expiry — not a settled P&L. That distinction is O1's central methodological finding
and it is checked rather than assumed: only **6.9%** of these paths lose their last usable quote
more than five days before expiry, so the continuation figures are not an artefact of stale
marks. (§3c re-checks it on the arms, where it matters more.)*

### 2e. THE CONTROL COMPARISON, and it is the most important line in stage 1

At **every** touch level and on **both** recovery measures — eight cells out of eight — the
**random-entry control recovers MORE often than the signal book**:

| from a touch of | back to ≥0: signal → control | to +100%: signal → control |
|---|---|---|
| −25% | 55.2% → **61.2%** | 28.3% → **33.3%** |
| −40% | 43.6% → **48.9%** | 21.9% → **25.5%** |
| −50% | 35.4% → **40.6%** | 17.5% → **20.6%** |
| −60% | 27.2% → **31.5%** | 13.2% → **15.4%** |

…while the drawdowns themselves are **identical** (mean MAE −39.7% on both books, medians
−51.5% vs −50.8%), and the control reaches +100% more often overall (**50.1% vs 44.7%**).

**The alert picks entries that dig just as deep and come back less often.** That is R2's verdict
restated in path terms, on a measurement R2 never made.

**NOT a sign test, and the temptation to call it one is exactly what this project has already
been burned by.** The four touch levels are nested subsets of one another (a −60% touch is a
−50% touch) and the two recovery measures are nested (reaching +100% implies passing 0), so the
eight cells are nowhere near eight independent draws — the same error SELRULE measured on X8's
countries, where 16 co-moving units were worth an `n_eff` of 2 to 4. The honest statement is
that **the direction is unanimous across every cut**, not that it carries a p-value. The
magnitudes (4–6pp) are consistent with R2's −6.65pp gap, measured a different way.

## 3. STAGE 2 — thirteen pre-registered arms. VERDICT: REJECT.

Stage 1 cleared the pre-registered materiality bar (§3 of the register: a recovery cell ≥10pp
from base on ≥100 trades — the ≤7-DTE cell is 26.2pp below on 153 trades), so stage 2 ran.

Gain in per-trade expectancy over the shipped policy, full book, with month-block clustered CIs:

| arm | family | gain | clustered CI95 | fires on |
|---|---|---|---|---|
| `trail50_after100` | A | **+3.60pp** | [−0.5, +7.7] | 9.6% |
| `escalate_fast` | F | +2.40pp | [−0.6, +5.7] | 11.1% |
| `half_at_100` | E | +1.93pp | [−0.2, +4.1] | — |
| `clean_runner` | F | +1.50pp | **[+0.4, +2.5]** | — |
| `time_cond25` | B | +0.12pp | [−0.4, +0.7] | — |
| `ivcrush30` | C | −0.02pp | [−0.2, +0.1] | 1.3% |
| `delta85` | C | −0.02pp | [−0.3, +0.2] | 2.4% |
| `stock_stop` | D | −0.06pp | [−0.2, +0.1] | **0.4%** |
| `be50` | A | −0.36pp | [−1.2, +0.5] | 9.9% |
| `step50` | A | −0.36pp | [−1.2, +0.5] | 9.9% |
| `extrinsic20` | C | −0.47pp | **[−0.9, −0.0]** | 4.4% |
| `gap_open` | D | −1.72pp | **[−2.4, −1.1]** | 5.6% |
| `sl_by_dte` | B | **−2.14pp** | **[−3.4, −1.0]** | — |

**The wall.** Book split at its median alert date, **2021-03-08**; arms ranked on the decide half,
the published number measured on the other; both directions:

| direction | arm selected on decide | decide gain | **measured on the other half** | clustered CI95 |
|---|---|---|---|---|
| decide early → measure late | `trail50_after100` | +1.42pp | **+5.77pp** | [−0.03, +11.95] |
| decide late → measure early | `trail50_after100` | +5.77pp | **+1.42pp** | [−4.15, +6.65] |

**Both directions select the same arm — which is more stability than session 7's LOO managed —
and neither measured gain clears the bar, and neither confidence interval excludes zero.**
The bar is **O1's own `MIN_EXPECTANCY_GAIN = 0.10`**, i.e. 10 percentage points of per-trade
expectancy, pre-committed there and re-committed in `PREREG_path_study.md` before any arm ran.
The largest **full-book** gain in the study is **+3.60pp**, and the largest gain on any
half-sample is the **+5.77pp** in the table above. Against a **10pp** bar, neither is close —
and the +5.77pp is the more flattering of the two directions of a split whose other direction
gives +1.42pp on the same arm, which is what a wall is for.

**VERDICT: REJECT. No rule change is justified, and nothing ships — not to the live book, not to
the paper book.**

### 3a. THE STRONGEST RESULT IN THE STUDY IS THE CONTROL, AND IT GENERALISES O23

The same thirteen arms were scored on the five pooled random-entry seeds (29,783 paths). The
control's shipped policy returns **+10.06%/trade — R2's recorded control mean, exactly**, which
is the second independent reproduction of the record this study produces.

| arm | gain on the SIGNAL book | gain on RANDOM entries | difference |
|---|---|---|---|
| `trail50_after100` | +3.60pp | **+3.46pp** | +0.14pp |
| `half_at_100` | +1.93pp | +2.04pp | −0.10pp |
| `escalate_fast` | +2.40pp | +1.74pp | +0.66pp |
| `clean_runner` | +1.50pp | +1.29pp | +0.20pp |
| `gap_open` | −1.72pp | −1.27pp | −0.45pp |
| `sl_by_dte` | −2.14pp | −2.72pp | +0.59pp |

Across all thirteen: **Pearson r = 0.967, regression slope 0.990, 13 of 13 the same sign, mean
absolute difference 0.34pp and a maximum of 0.86pp.**

**Whatever an exit rule does to the alert's book, it does to a book of random entries — one for
one.** O23 found that *half* of an exit's P&L difference is the underlying. On this arm set, on
this book, essentially **all** of it is independent of the entry. An exit rule is a property of
options, not of the signal.

Under O1's own gate that is the *supportive* branch — `X1_adopt` requires an arm to help on both
entry sets, precisely so that a book-specific fit is caught. These arms are not fitted to the
book. They simply do not clear the magnitude bar, on either book.

### 3b. Three things the rejection should not be allowed to bury

1. **`sl_by_dte` is the worst arm in the study, and it is the one stage 1 appeared to motivate.**
   Stage 1 says recovery collapses as DTE shrinks; the conventional stop-widening parameterisation
   pre-registered for family B (−40% while DTE > 21, −60% at DTE ≤ 21) **widens the stop exactly
   where stage 1 says the trade is already dead**, and it costs −2.14pp with a CI excluding zero.
   The register fixed that parameterisation before stage 1's table existed. **The flipped version
   — tighten near expiry — is a NEW pre-registration for a future session, and running it now on
   the same book would be selecting the rule on the result.** That is the whole reason the arms
   were committed first.
2. **Families C and D are nearly inert, and that is a structural finding.** `stock_stop` fires on
   **0.4%** of trades, `ivcrush30` on 1.3%, `delta85` on 2.4%. By the time the underlying is −8%
   the option is already through its −50% stop: **the option-level stop dominates every
   underlying- or state-level trigger tested.** An underlying-triggered exit has almost no room
   to act inside this policy.
3. **`be50` and `step50` are the same arm.** Identical exits, identical mean, to the digit —
   because with a +50% step the first ratchet lands exactly at breakeven and the +100% target
   closes the trade before a second step can arm. Two of the thirteen arms are one arm; the
   register did not notice, and the run did. Counted and charged as two, because that is what was
   pre-registered.

### 3c. The stale-mark control, which is what makes the hold-longer arms quotable at all

O1's central methodological finding is that marking a dying contract at its last usable quote
manufactures a **monotone reward for holding longer**. Four of these arms hold longer. Measured:
only 7–13 trades per arm reach the expiry path at all, and **zero of them use a stale mark** —
every one settles at intrinsic. So `trail50_after100`'s +3.60pp is a real property of the paths
and *still* fails the bar, rather than being an artefact that had to be argued away.

## 4. Plain answer for Don

**Your exit policy is in better shape than the study set out to test, and the one part that looks
wrong is the part that refused to improve when I tried.**

* **"Do my losers come back if I give them room?" — No, and the −50% stop is roughly where it
  should be.** Once a trade touches −50%, its chance of ever reaching +100% falls from 44.7% to
  17.5%, and only about a third ever see breakeven again.
* **"Should I let winners run past +100%?" — The data says take the double.** Two thirds of early
  winners do double again, but 83% give back the +100% and **58% eventually go to a loss**.
  Holding is a lottery ticket bought with a sure thing.
* **"Is the half-DTE time stop cutting my winners short?" — No.** Winners arrive in a median of
  20 days, a third of the contract's life, and two thirds of them arrive with more than half the
  time still left.
* **"Should the stop depend on how much time is left?" — The paths say yes and the test says no.**
  A −50% drawdown with a week to go recovers 9% of the time; with two months to go, 42%. That is
  the strongest structure in the whole study — and the time-conditioned stop I had committed to in
  advance made things *worse*, by −2.14pp. I am not going to rewrite the rule on the strength of a
  pattern whose one pre-registered test failed.
* **Nothing changes.** No rule ships, to either book. And none of this is a reason to trade the
  options alert — the entry is still dead; this was about how the paper book exits, and about
  knowing how these contracts behave.

## 5. BUGS FOUND

**B-PATH.1 — `scripts/path_study.py` would have failed the auto-land gate on a fresh checkout,
and my own local runs could never have shown it.** `_data_root()` raised `SystemExit` at import
when it found no `data/options_freeze`. `data/` is gitignored, so **CI has none** — and
`tests/test_path_study.py` imports the module. On a fresh checkout the suite would have aborted
before a single test ran. It never fired locally because a worktree finds the primary checkout's
data three levels up, which is precisely the class of defect a developer machine cannot see.
**Fixed** (absent data now degrades to a non-existent path, so the error lands where a file is
opened, not where a module is imported) and **verified against the real failure mode**: copying
the tree without `data/` and restoring the old function reproduces `no data/options_freeze
found` with zero tests run; with the fix, 25/25 pass. Pinned by
`TheModulesImportWithoutTheLicensedData`.

*This is the same shape as LA15 earlier in this session — a test outcome that depends on
machine-local state — arriving from the other direction: there a test read state CI lacks and
passed anyway; here a test read state CI lacks and would have died.*

## 6. What was NOT done, and where it went

* **Earnings-timing arms → O17. Sizing → O12.** Excluded by the register's own scope, observed
  and not run. One observation for O12 from §2d: the post-target distribution is so barbelled
  (p25 −94.4% against a median +62.2%) that position sizing, not exit timing, is where the
  variance actually lives.
* **The flipped `sl_by_dte`** — tighten near expiry rather than widen — is the one arm this study
  ends up wanting and may not run. New pre-registration, future session, ideally different data.
* **No live-book or paper-book change was made**, so nothing needs deploying and nothing needs
  reverting.

## 7. Trial accounting

Stage 1 is descriptive: no arm, no bar, no verdict, **zero trials**. Stage 2 charges its
**13 arms to options `N`**, as the register committed, whatever the verdicts —
options **192 → 205**. Equity `N` is untouched at **135**, so no DSR-gated equity claim moves.

---

# ITEM A — THE TAKE-PROFIT BAR: a decision memo, not a change (2026-08-10)

Full memo, written as a pre-registration: **`PREREG_A_take_profit_bar.md`**. It ends at Don's
choice and **changes no policy**, exactly as `PAPER_TRACK_CONTRACT.md` did. Ledger row `TP-BAR`.

`HANDOFF_parked_positives.md` item A is the one entry on that list whose missing input is a
judgement rather than data: raising the take-profit +100% → +150/200% is measured twice and was
refused by a **+10pp per-trade** bar. **The caveat travels with every option below: the entry
signal is dead (R2, −6.65pp vs a five-seed control, sign-test z −4.903), so nothing here makes the
options alert tradeable.** This is about how a paper book exits.

## 1. The three looks reconciled — and the inventory's independence claim is too strong

| # | run | trade set | baseline | `tp150` | `tp200` |
|---|---|---|---|---|---|
| 1 | deep-research, 2026-08-03 | 3,119 / 5,986 | +4.708%/trade | +2.11pp | +3.26pp |
| 2 | O1 off the freeze, 2026-08-08 | **3,885 / 29,785** | +3.410%/trade | **+3.19pp** | **+3.82pp** |
| 3 | path study F-family, 2026-08-10 | **the same 3,885** | +3.410%/trade | — | — |

Look 3 tested no raised target directly (its families were path-*conditional*), but everything it
ran in that direction leans the same way and lands in the same range: `escalate_fast` **+2.40pp**,
`clean_runner` **+1.50pp**, `trail50_after100` **+3.60pp**. None cleared.

**Measured, not asserted: look 1 and look 2 share 1,099 trades — 35.2% of look 1, 28.3% of look 2
— and look 3 runs on look 2's book exactly.** So item A's *"replicated in two independent runs"*
overstates it. What we own is **two partially-overlapping trade sets and three analyses**. The
direction has never disagreed (five positives from five looks, two books, two entry sets), but it
is one option corpus examined three times. Also: the inventory's `+3.19/+3.82` are look 2's; look
1's own artifact reads `+2.11/+3.26`. Anyone quoting item A should say which book.

## 2. Why +10pp was the wrong bar — from the distribution, not from wanting to pass

* **Attainability, measured over all 33 exit arms ever scored on the 3,885-trade book: exactly
  ONE clears +10pp.** `tp100_only` at **+10.78pp** — and it **fails paired-cell FDR**, raises tail
  concentration from 86.75% to **92.75%**, and (inventory item J) fails the name-year sign test on
  the alert book at **z −5.76** while passing on random at +10.55. **A bar that only a discredited
  arm can clear is not selecting for quality; on this family it is selecting for removing the
  stop.**
* **The unit is the real problem, and lowering the number does not fix it.** This book's
  expectancy is a tail statistic — hit rate 35.3%, median trade −52.2%, **86.75% of gross winnings
  from the tail**. The *gains* are worse: over the per-trade differences, the **top 1% of trades
  carry 106–210% of each arm's entire gain**, so the other 99% are collectively negative. "+3.82pp
  of expectancy" is a claim about a few dozen contracts.
* **THE OBVIOUS FIX IS REFUTED BY MEASUREMENT, and it was the one I expected to endorse.** "Use a
  relative bar, the payoff is multiplicative" fails on the two books we have: between look 1 and
  look 2 the **absolute** gain drifts +17% (`tp200`) and +52% (`tp150`), while the **relative**
  gain drifts **+62%** and **+109%** — because the baseline expectancy itself fell −27.6%.
  **The absolute figure is two to four times the more stable unit.** Reported because it cuts
  against the case for adopting.
* **The bar is also nowhere near the design's resolution.** Month-block clustered SEs on the
  paired gain run **0.29pp to 2.10pp**, so the design resolves ~0.6–4.2pp at |t| = 2. A 10pp bar
  sits an order of magnitude from the noise, in a region this family never visits.

## 3. What the memo pre-registers instead — a procedure, not a number

**What a paper-book bar is FOR, which is what fixes its shape.** A bar on a live-money change is
an *economic* instrument — "is this worth the cost and risk of doing?" — and a large absolute
threshold is reasonable there because small edges do not survive frictions. A bar on a **paper**
book is an *epistemic* one: no money moves, it reverses in one constant, and §4 shows it breaks no
forward-record continuity. The cost of adopting a small *true* improvement is ≈ 0; essentially the
whole downside is adopting an artefact of having looked at the same 3,885 trades three times.
**So the bar should be sized to separation from noise, not to materiality — and a large absolute
pp threshold is a materiality test wearing a significance test's clothes.** That, not its level,
is why +10pp was the wrong instrument.

**And it deliberately names no replacement level.** Any number argued in prose would be a number
chosen after seeing which arms pass. X7 is the precedent: measure what the null produces and take
a percentile. So the memo commits to **C1** a calibrated level (p95 of a null built by jittering
exit parameters, n=100, seeds 1000–1099, identical paths and scorer, binding whatever it returns
— including a bar above +3.82pp that refuses the change again); **C2** a condition that does not
run through the mean (the gain must survive winsorising the top 1% of per-trade differences — a
real hazard given the table above); **C3** entry-independence, already satisfied; **C4** the
existing FDR / both-halves / both-sets / PBO gates. **No new market data is required for any of
it.**

## 4. The timing fact most likely to be assumed wrong

**The paper options book holds three positions — TGT, ETN, MET — all OPEN, and ZERO closed
trades** (verified against the committed export). A policy change now breaks **no** forward-record
continuity, because no options exit has ever been recorded. That makes "adopt" *cheap*, not
*right* — and it expires with the first closed trade. Checked and not assumed: no vintage closes
either, because the contract binds the published **Index**, not this book.

## 5. The three options, as put to Don

1. **Adopt `tp150` on the paper book now.** Accepts +3.19pp against a bar revised after seeing the
   numbers, and gives up the right to say it cleared a pre-committed bar. `tp150` over `tp200`
   because `tp200`'s extra +0.6pp costs hit rate 35.3% → 31.3%, target exits 27.1% → 13.4%, and
   three extra days of hold. Zero trials, reversible in one constant.
2. **Require one confirmation (C1–C4), then decide.** No new data, one session's compute. Placebo
   calibration charged **zero** (X7 / HACFLOOR precedent); the two winsorised re-scores charged
   **2** to options `N` (205 → 207). May well refuse the change — which would close item A
   properly rather than leaving it parked.
3. **Leave it.** The shipped +100% is defensible on the path study's own evidence: **83.2%** of
   early winners give the +100% back and **58.0%** eventually go below zero if held.

**My recommendation, recorded so it can be scored later: option 2**, and the pre-registered
expectation is that the calibrated bar lands between +1pp and +4pp (60/40) with `tp150` clearing
it *barely* (55/45).

## 6. Trial accounting

**Zero.** No arm scored, no hypothesis tested, no bar applied — every figure is a re-cut of banked
artifacts plus one read of the committed paper-track export. Options `N` stays **205**, equity
`N` stays **135**, `rows_malformed` empty.

**And deliberately NO `RESEARCH_LOG.md` row, which is a decision rather than an omission.** That
file's counting rule is *"all non-FIXED rows count"*, so adding a row — even one marked
`REGISTERED` — would charge a trial against a document that tests nothing. V1's `REGISTERED` row
is not the precedent here: it registered an instrument that had been **built**. This registers a
**procedure that has not run**, and the nearer precedent is SELRULE, where declining to run a test
cost zero and the reasoning was recorded in the ledger. **The ledger row `TP-BAR` is the record.**
If Don picks option 2, that run gets the research-log row and the 2 trials, on landing.

---

# SESSION 22 — 2026-08-11 — TP-BAR: **Don chose Option 2, and item A closes REJECTED**

**Don's choice, recorded with its date:** Option 2 of `PREREG_A_take_profit_bar.md`, taken
**2026-08-11** — decide the take-profit question against a bar that is *measured* rather than
chosen. The confirmation was run exactly as §3 pre-registered it. **No policy changed. Item A is
closed, not re-parked.**

**THE CAVEAT TRAVELS, as it must:** the options entry signal is dead (R2 — the alert book returns
+3.41%/trade against a five-seed random-entry control's +10.06%, paired sign test z −4.903).
Nothing here is a tradeable-edge claim; it decides how a **paper** book exits.

## 1 · The verdict in one table

| | `tp150` | `tp200` |
|---|---|---|
| **C1 — clears the calibrated bar (+5.0812pp)** | +3.1948pp — **FAILS** | +3.8238pp — **FAILS** |
| *percentile within its own family* | **82nd** | 87th |
| **C2 — positive after winsorising the top 1%** | +2.4511pp — **PASSES** | +3.0161pp — PASSES |
| **C3 — holds on the five pooled random seeds** | +2.5969pp — **PASSES** | +3.8986pp — PASSES |
| **C4 — FDR / both halves / both sets / PBO** | **PASSES** | PASSES |
| **VERDICT** | **REJECTED — fails C1 only** | **REJECTED — fails C1 only** |

## 2 · The bar was committed before the arm was scored, and that is visible in git

`e8e5505` contains `scripts/tp_bar.py`, its 16 tests, and §8 of the memo carrying the bar —
**with `scripts/tp_bar_score.py` not yet written**. The scorer is a *separate module* that
**reads** the bar from C1's artifact and `load_bar()` **refuses to run** if that artifact and the
figure published in the memo disagree by more than 5e-4. A test also fails if the scorer ever
defines its own ranges or percentile.

**The bar: +5.0812pp**, the p95 of 100 jittered draws from the arm's own family — target
0.50–2.00, stop −0.30 to −0.70, time-stop fraction 0.25–1.00, **endpoints read off
`options_exitlab.POLICIES` rather than chosen here** (three tests fail if they drift), seeds
1000–1099, identical frozen paths, identical `apply_arm`, every draw paired on all 3,885 trades.
Null **min −6.786, p5 −4.570, median +0.803, max +8.111, 53 of 100 beating shipped**.

## 3 · The harness reproduces the record independently — the control that makes it quotable

This scorer was written for the **path study**, not for O1. It returns `shipped` at
**+3.410308%/trade** (R2's headline) and gains of **+3.1948 / +3.8238pp** against O1's banked
`expectancy_diff` of **0.031947661 / 0.038237652** — the same numbers to four decimals, from a
separately-written path re-build. Two independent implementations agreeing to that precision is
the strongest cross-check this lane has produced.

## 4 · The result is sharper than a plain "no" — and must not be over-read

**`tp150` passes every condition except the calibrated one.** The memo predicted **C2** would be
the hazard; C2 was passed comfortably — capping the top 1% of per-trade differences at +124.3pp
(39 trades) still leaves **77%** of the gain. So the raised target is **not tail-driven**, it is
**not** an entry artefact, and it is FDR-significant and positive in both halves of both books.

**What it is not is *distinguished within its own family*.** It sits at the **82nd percentile** of
arbitrary jitters when the bar was the 95th. **53 of 100 random tweaks beat the shipped rule**,
the median by +0.80pp and the best five by +5.2 to +8.1pp — all the same *wider stop, higher
target, hold longer* shape. **When a whole region of parameter space looks good on one corpus,
that corpus cannot tell you where inside it the optimum is**, and picking one point from it after
five looks is choosing by hindsight. That is the hazard item A carried; the bar priced it.

**The objection, stated rather than left for a reader to find:** a narrower null would give a
lower bar and `tp150` might clear it. True — and precisely why the construction was fixed in §3
*before* it ran and bound "whatever it comes out as". **Choosing the null after seeing which one
passes the arm is the move the whole exercise exists to refuse.**

## 5 · The by-product that is unflattering to the shipped rule

**The inherited +100%/−50%/half-DTE exit sits slightly *below* the median of its own family** —
beaten by 53 of 100 jitters, by +0.803pp at the median. It is an ordinary member of its family,
not a local optimum. **It cannot be acted on for exactly the reason `tp150` was refused**, and it
is recorded so that nobody later presents the shipped exit as having been *validated* here. It
was not. It was left in place.

## 6 · The pre-registered expectation was **wrong three times out of three**

| prediction (memo §6, written first) | odds | outcome |
|---|---|---|
| bar lands **+1 to +4pp** | 60/40 | **WRONG** — +5.0812pp |
| `tp150` **clears** it | 55/45 | **WRONG** — fails at the 82nd percentile |
| `tp200` clears but **fails C2** where `tp150` passes | 50/50 | **WRONG both halves** — `tp200` failed C1, and C2 passed for both |

Consistent with the standing record: **do not reason about the direction of an effect in this
project; measure it.**

## 7 · Accounting

**2 trials** for the two winsorised re-scores, as committed. **Options `N` 205 → 207.** The C1
calibration is charged **zero** (X7 / session-10 HAC-floor precedent — a calibration searches
nothing). **Equity `N` is untouched by this work but is no longer 135 — it reads 143**, moved by
S22's eight horizon arms landing from another lane mid-session; flagged because a stale `N`
overstates every DSR-gated claim. `rows_malformed: []`.

## 8 · What I did NOT do, and why

* **No policy changed anywhere.** The paper options book keeps +100% / −50% / half-DTE. The
  verdict was mechanical and it came out REJECTED, so there was nothing to ship.
* **Did not re-run C3/C4 from scratch.** Both are already measured on this exact book by O1 and
  are **read from `EXITLAB_FROZEN_2026-08-08.json`**, so the verdict cites banked numbers. The
  first extraction returned `null` for the random-book gains because I used the wrong key path;
  fixed and re-run rather than reported blank.
* **Did not re-open the "narrower null" question.** It would be a new pre-registration, and
  running it now — after seeing that the current null refuses the arm — is selecting the rule on
  the result. Same reason the flipped `sl_by_dte` was left alone last session.
* **Did not touch item A's *other* recorded claims** beyond the two the work corrects (the
  "two independent runs" and the +10pp framing), both struck in place in
  `HANDOFF_parked_positives.md` rather than deleted.

## BUGS FOUND

**1 — `VALQUO_LEDGER.md` has two rows with unescaped `|` in their note text, and one of them is
the row that documents this exact defect class.** Found while checking my own row's shape, not
looked for. Every well-formed ledger row splits to **12** cells; **170** do. Two do not:

* **`VALQUO_LEDGER.md:341`, row `M1-PARSE` — 15 cells (3 extra).** The offender is
  `` |Spearman(term_slope, atm_front)| `` written literally inside the cell. **This is the row
  whose entire subject is session 12's discovery that an unescaped `|` in a markdown cell shifts
  every column after it** — it quotes the offending O16 string without escaping it and thereby
  reproduces the defect it describes.
* **`VALQUO_LEDGER.md:360`, row `V2G` — 14 cells (2 extra).** The offender is `max|dev|`, the
  absolute-value bars.

**Severity: low, but not zero, and it is the harmful direction.** `build_ledger.py` preserves
out-of-band rows verbatim so it does not corrupt them, and `research_log.detail()` reports
`rows_malformed: []` because these are in the *ledger*, not the research log — the trial
denominator is untouched. The exposure is to any reader or tool that addresses ledger columns
**by position**: for these two rows the status, date and lane columns are shifted right, so a
positional read gets prose where it expects a verdict.

**Not fixed by me, deliberately.** Both rows belong to other lanes (`M1-PARSE` to the parser lane,
`V2G` to the greeks lane) and the register's own rule is that a landed row's text is not edited by
someone else. **The fix is one character each — escape as `\|`** — and it is theirs to make.

**2 — one defect of my own**, caught by my own test and fixed before landing:
`tests/test_tp_bar_score.py` asserted that the 99th percentile of `[0]*99 + [100]` *is* the
outlier, so nothing would be capped. It interpolates to 1.0 and the outlier **is** capped — the
code was right and the assertion was wrong. Corrected with the arithmetic spelled out in the
test, rather than by loosening it.


# SESSION 23 — 2026-08-11 — U1: **the equity edge does NOT reach the options book**

U1 was the ledger's oldest blocked unification item and the first test of whether the one thing
this project has that survives calibration — the equity composite — is worth anything on the
options side. It is now **REJECTED**, and a **corporate-action defect found on the way moves a
published R2 headline by 24%.**

Pre-registered in `PREREG_u1_composite_entry.md`, committed **alone at `7d7c414`** before any U1
code existed. Bars committed at **`e34dc9d`** with the scorer not yet written.

---

## 1 · The verdict in one table

| | TOP10 | TOP20 | BOT10 |
|---|---|---|---|
| n | 486 | 948 | 557 |
| mean/trade | +2.4624% | +4.6726% | +11.3446% |
| **gain vs grid** (grid = +3.6516%) | **−1.1892pp** | +1.0210pp | +7.6930pp |
| V1 plain bar +7.2870pp | **FAILS** | FAILS | clears |
| V2 cap-matched bar +9.4513pp | **FAILS** | FAILS | clears |
| percentile in its own null | **31st / 15th** | 63rd / 48th | 99th / 99th |
| V3 date-block CI95 | **FAILS** [−11.74, +10.29] | FAILS | FAILS [−1.53, +17.26] |
| V4 both halves positive | **FAILS** (+5.18 / −5.61) | passes | passes |

**TOP10 fails all four and its gain is NEGATIVE, so the registered rule fires REJECTED.**

## 2 · The reopen condition was met both ways at once

`VALQUO_LEDGER.md:300` said *DO NOT RUN AS WRITTEN … reopen only with a composite built WITHIN
the options universe **or** with size neutralised.* This design did both: rankings are
percentiles among the ~182 optionable names as of the same rebalance date, **and** the primary
null is drawn **matched on market-cap tier per date**.

That second null earned its keep before any arm was scored: **its median gain is +2.8933pp
against the plain null's +0.5366pp.** The top decile's *cap-tier mix alone* is worth ~+2.4pp —
**U7's mechanism, reproduced inside the null**. It is why the cap-matched bar is the harder one
and why TOP10 sits lower in it (15th percentile vs 31st).

## 3 · The mechanism is cleaner than the verdict

**Every decile's MEDIAN trade is between −52.5% and −54.3%. All ten.**

| | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| mean | +2.46 | +7.00 | +6.98 | +4.67 | +1.92 | +5.03 | +2.60 | −0.09 | −4.89 | +11.35 |
| median | −52.8 | −52.9 | −52.5 | −52.9 | −53.0 | −52.5 | −53.3 | −53.3 | −54.3 | −52.6 |

**The composite does not move the typical option trade at all.** Every decile difference lives in
the right tail, and the right tail on ~500 trades is exactly what a +7.29pp bar calls noise.
**TOP10's mean is entirely tail-carried — its best five trades are +3.912pp of a +2.462% mean,
158.9% of it.** Strip them and it is negative outright; winsorised the gain worsens to −1.4911pp.

## 4 · The strongest number, and it cuts against the composite

On **R2's standing statistic** — the paired name-year sign test, within `(ticker, year)`, so it
asks whether a name's top-decile quarters beat its own other quarters:

* **TOP10: 119 of 285 cells, 41.8%, z −2.7840, p 0.0054**
* **TOP20: 210 of 489 cells, 42.9%, z −3.1203, p 0.0018**

Two arms, same direction, the wider one stronger. **Limit stated: no calibrated bar exists for a
paired within-grid sign test**, so these p-values are conventional and uncalibrated.

## 5 · BOT10 clears both bars and is NOT a finding — do not act on it

The **worst**-composite decile gains +7.6930pp at the **99th percentile of both nulls** and
survives winsorising. It is still refused, on grounds fixed before the run: its date-block CI
**includes zero**; it is **carried by the late half** (+1.13 vs +12.47); and its **sign test is
52.0%, p 0.4681** — it does not win more *often*, it wins *bigger*.

**"The composite runs backwards" would be the exact error TP-BAR closed.** The decile table is
**UNORDERED, not INVERTED** — D9 is the worst cell and D10 the best, which no monotone story
explains. The mechanical `backwards` clause did fire and is recorded, but the negative gain alone
was already sufficient, and **"inverted" is the wrong word and must not travel.**

## 6 · BUGS FOUND — `U1-SPLIT`, and it moves a published headline

**Option chains are as-traded and unadjusted for splits; bars are adjusted; nothing in the
options lane has ever consulted the split table** — though `bulk.py:312` documents the hazard in
so many words. The signature is a **reverse** split: **GE went 1-for-8 on 2021-08-02**, so a
$14-strike call bought 2021-07-23 at **$0.27** settles against a ~$104 post-split underlying on a
strike never re-based and books **+31,921%**. That **one row is 6.28pp of the raw grid's 9.93%
mean** — 62% of its entire expectancy.

| book | as published | split-clean | move |
|---|---|---|---|
| R2 alert book | +3.4103% | +3.2702% | −0.1401pp (15 rows) |
| R2 five-seed control | +10.0571% | +8.3342% | **−1.7229pp** (131 rows) |
| **R2 gap** | **−6.6468pp** | **−5.0640pp** | **24% of it is an artifact** |

**The control is hit ~12× harder** (many random days per name-year = more shots at any split
window; two GE draws at +269x and +261x), **so the defect has been making R2's negative verdict
look WORSE than it is, and correcting it runs toward the alert.** R2's sign, significance and
verdict are **unchanged** — the alert still loses decisively — but **quote −5.06pp, not −6.65pp.**

Found **before any arm was scored**, provable: the bar commit contains no scorer. The exclusion
is keyed on an **external table and a date**, never on the size of a return — two tests enforce
that a +50,000% return on a split-free name **survives** and a +0.1% return on a split-crossing
name is **dropped**. **The repair belongs upstream in the miner/replay path and is NOT DONE**;
U1 excludes, it does not re-price.

## 7 · The expectations: **3 right, 2 wrong, 1 untriggered**

E1 NULL → **REJECTED, wrong**. E2 gain 0 to +4pp → **−1.19pp, wrong**. E3 cap-matched binding
*if* V1 passes → **untriggered** (V1 failed first; spirit held). E4 decile table not monotone →
**right**. E5 grid beats the alert → **right, +0.3814pp**. E6 E5 survives the split fix →
**right, and narrow**.

## 8 · What I did NOT do, and why

* **Did not act on BOT10**, for the reasons in §5. Acting on the extreme of three arms whose own
  date-block CI includes zero is the move this lane exists to refuse.
* **Did not repair U1-SPLIT at source.** That is a miner/replay change touching every banked
  options result; it needs its own register and re-bank. U1 only excludes.
* **Did not re-run R2, TP-BAR or the path study on split-clean data.** Their verdicts are
  unchanged in sign; their magnitudes are not, and re-banking is the upstream owner's call.
* **Did not test a composite built within the options universe from options-native inputs.**
  That is U2, a different hypothesis, and would need its own pre-registration.
* **Changed no live behaviour.** No policy, no weight, no constant. The paper options book is
  untouched; the contract binds the Index, not this book.

## 9 · Accounting

Three scored arms: **options `N` 207 → 210**, verified from `research_log.detail()`
(`rows_malformed: []`). The grid mine and both calibrations charged **zero** on the X7 /
session-10 precedent. **Equity `N` reads 149, not the 143 this session started quoting** — S23's
six arms landed from another lane mid-run, and a stale `N` overstates every DSR-gated claim, so
it was re-measured rather than copied.


# SESSION 23b — 2026-08-11 — `U1-SPLIT` **repaired at source**. R2's published gap was 24% artifact; **no verdict moved.**

My own finding from U1's calibration, chased to the end. Pre-registered in
`PREREG_u1split_repair.md`, **committed alone before any repair code existed**, naming the eight
published figures that move and the expected direction of each.

---

## 1 · Reproduced from the bars before anything was touched

`options_backtest.simulate_trade` settles at intrinsic against `bars["raw_close"]` — the
**unadjusted** close, with the comment *"as-traded: strikes are not adjusted"*. Correct **within**
a split-free window, wrong **across** one.

| date | `raw_close` | `adj_close` |
|---|---|---|
| 2021-07-30 | 12.9500 | 63.3710 |
| **2021-08-02** (GE 1-for-8 reverse) | **100.6000** | 61.5360 |
| 2021-09-17 (expiry) | 100.4700 | 61.4570 |

The banked row: strike 14.00, entry 0.2700, exit **86.4700** — and `max(0, 100.4700 − 14.00) =
86.4700` **to the cent**. **The true value is not "unknowable", it is ZERO**: the OCC adjusts the
*deliverable* to 12.5 new shares and leaves the strike, so true P&L is **−100%** against a booked
**+31,921%**.

## 2 · The exposure was wider than my first diagnosis, and that changed the repair

**106 of the 131 affected control rows never reach the settlement line** — they exit on target or
stop, i.e. on **post-split quotes**. A reverse split keeps the strike, so `contract_history`,
which matches on exact strike, happily returns quotes referring to an adjusted deliverable. A
settlement-only patch would have left the larger channel open.

**So the guard rejects at ENTRY, on the contract life `(entry, expiry]`, decided before
simulation** and therefore provably outcome-independent. Dropping only trades whose *exit* lands
after the split would be keyed on exit timing — which is determined by the payoff.

**Exclusion, not re-pricing, with the direction disclosed:** since the flagship case's true value
is −100%, re-pricing would push the control's mean *further* down and help the alert *more*.
**Exclusion is the conservative choice against R2's standing negative verdict.**

## 3 · The control first: every as-published figure reproduces to the digit

Gap −6.6468pp · CI95 [−11.9152, −2.1317] · sign z −4.9027 over 1,334 cells · breadth +9.3720% /
−0.4713% · design effect 2.2121 vs null p95 1.2037 · TP-BAR bar +5.0812pp with `tp150` +3.1948pp
at the 82nd percentile · shipped +3.410308%/trade. **A re-derivation that could not reproduce the
old numbers would be evidence about the harness, not the defect.**

## 4 · The headline moves; the verdict does not

| | as published | **split-clean** |
|---|---|---|
| alert book | +3.4103% | **+3.2702%** |
| five-seed control | +10.0571% | **+8.3342%** |
| **gap** | **−6.6468pp** | **−5.0640pp** |
| date-block CI95 | [−11.9152, −2.1317]pp | **[−8.5957, −1.5325]pp** |
| sign test | −4.9027, 1,334 cells | **−4.9612, 1,332 cells, p 7e−07** |

**24% of the published gap was a corporate-action artifact.** The control is contaminated ~12×
harder (131 rows vs 15) — many random days per name-year means more shots at any split window —
so **the defect was making R2 look WORSE than it is.**

**REPORTED BECAUSE IT CUTS AGAINST THE OBVIOUS READING: the sign test does not weaken, it
STRENGTHENS** (−4.9027 → −4.9612). The mean gap shrank because the artifact lived in the
control's right tail; the median name-year cell never depended on it.

## 5 · P7 — the one that could have reopened item A. **It does not.**

| | as published | **split-clean** |
|---|---|---|
| C1 bar | +5.0812pp | **+5.1302pp** |
| `tp150` | +3.1948pp (82nd) | **+3.1834pp (81st)** |
| `tp200` | +3.8238pp (87th) | **+3.8653pp (87th)** |

**Both arms still FAIL C1 and the margin WIDENS** — `tp150`'s shortfall 1.8864 → 1.9468pp. The
bar moved *up*, the gain moved *down*: both against the arm. **Item A stays closed.**

## 6 · Fingerprints re-stamped

* **Freeze verified, not asserted: 1,429 symbol-years checked, 0 changed.** The repair never
  writes to `data/options/`, so every banked replay pin still holds.
* Corrected books are **new files**; **originals are never overwritten** — they are the record of
  what was published and are needed to check this correction. `U1SPLIT_MANIFEST.json` carries
  sha256 of both sides of all six books.
* **Equivalence verified:** re-mining 2021-07-22 under the guard gave 146 trades vs 147 banked,
  the dropped row was GE, key sets matched, **0 of 146 shared trades differed on any field**.

## 7 · BUGS FOUND

* **A defect in my own repair, caught by the repair's own check.** `u1_entry._mine_cell` collapsed
  every simulation failure to `no_trade`, so the guard worked but **could not be seen working** —
  against this register's own promise that rejections would be counted and named. Found by the
  equivalence check, not by reading the code. Fixed and pinned.
* **`CLAUDE.md` said "133 new names"; it is 132.** `UNIVERSE_RESULTS.json` has always read 132.
* **O20's `z −3.475` does not reproduce and is NOT restated.** The construction that reproduces
  every other O20 figure gives **−4.8953** as published. It is in no shipped artifact, so it
  cannot be reconciled from the repository. Recorded as unreconciled rather than replaced with a
  number that merely agrees in direction — that is how the 1.85 design effect travelled out of
  scope. **Owner: the O20 lane.**

## 8 · What I did NOT do, and why

* **Did not re-price.** §2 gives the reason and the direction it costs.
* **Did not re-mine the books.** Equivalence was verified instead; re-mining ~34,000 trades to
  reach a provably identical set would spend hours for nothing.
* **Did not edit sections 1–9 of `PREREG_A_take_profit_bar.md`, nor overwrite `TPBAR_NULL.json`.**
  Registers and banked artifacts record what was measured then. The re-derivation is an additive
  §10.
* **Did not re-run the path study, O1/exitlab or the autopsy split-clean.** Their inputs move by
  the same 15 rows; none of their verdicts rests on a margin this small, and re-banking them is
  the owning lane's call. Flagged, not done.

## 9 · Accounting

**Zero trials, as committed** — a correctness repair tests no hypothesis, and charging one would
create an incentive to leave defects unrepaired. Options `N` stays **210**, equity **149**. **No
research-log row**: that log is one row per pre-registered *test*. Expectations scored **6 right,
1 wrong** (D3 assumed a correction that shrinks a mean must weaken the statistic built on it —
different objects).

---

# SESSION 24 — 2026-08-11 — `O13` + `O12`: **the anti-signal is diffuse and un-tradeable, and the dead entry costs 2.75× in position size**

Two ledger items, one session, frozen book, no re-mine, exit policy untouched. Both registers
were committed **together and ALONE** at **`b0f287d`** — two `.md` files, **zero `.py`** — so the
ordering is provable with `git show --name-only --format= b0f287d` rather than asserted.

**Neither item re-opens R2.** The options entry is dead: split-clean the alert book earns
**+3.2702%/trade** (n 3,870) against a five-seed random-entry control's **+8.3342%**
(n 29,654), gap **−5.0640pp**, paired name-year sign test **z −4.9612**. O13 characterises the
corpse; O12 asks what the corpse's payoff distribution implies about size.

---

## 24 · `O13` — where the anti-signal lives. **DIFFUSE. The inverse is a NULL.**

### 24a · The structural fact that shaped the design, found before the register was written

Measured on the banked books and **disclosed in §1 of the register**:

| | alert book | control book |
|---|---|---|
| `score`, `iv`, `labels`, `flow_read` | ~100% | **0.0%** |
| `dte`, `target_delta`, `cap_tier`, `marketcap`, spreads, `pit_*` | 100% | 100% |

A random entry has no alert to describe it, so **the control carries none of the alert's own
features**. Those reach it only through the `_control_for` back-link, which maps **29,564 of
29,654 control rows (99.7%) to exactly one alert, with zero ambiguous**. A control row is then
bucketed by its **parent alert's** feature value, and the comparison reads *"on alerts that
looked like this, did the alert's chosen day beat random days on the same name?"*. The 90
orphans are dropped, never defaulted — a control row carrying a made-up feature value would be
silently mis-binned, which is the exact failure the join exists to avoid.

### 24b · THE PRIMARY FINDING, and it is not the verdict

**The gap is entirely a WITHIN-BIN effect. Essentially none of it is composition.**

Across **all 32 arms** the *rate* component (alert mix held fixed, gaps measured inside bins)
sits between **−4.23pp and −5.79pp** against a total gap of **−5.0640pp** — while the largest
*mix* component anywhere in the 32 is **0.7711pp, i.e. 15.2% of the gap**, and most are under
0.2pp.

> **The alert does not lose because it picks different CONTRACTS from random entry. It loses
> inside every kind of contract it picks.**

That is worth more than the verdict, because it closes off a whole family of repairs. "Trade
longer-dated", "trade tighter spreads", "trade bigger names" are all *composition* fixes, and
composition is not where the damage is. Whatever the alert is doing wrong, it is doing it to the
**day it chooses**, uniformly.

### 24c · Q2 — concentrated or diffuse? **DIFFUSE.**

The statistic was fixed in advance: `S_worst`, the share of the rate component carried by a
feature's single worst bin — **0.20 if perfectly diffuse over five bins, 1.00 if perfectly
concentrated**. The bar is each feature's **own p95** over 2,000 draws of a null that holds every
row's `(book, return)` fixed and permutes bin labels **within book**, which **preserves the total
gap exactly** and destroys only the feature↔return association.

**Nothing clears its own p95 in both halves.** Four of 32 clear on the full sample — `labels:Uptrend`,
`labels:Low IV 18%`, `labels:Volume surge 1.6x`, `pit_atm_oi` — against **~1.6 expected at a 5%
bar over 32 correlated arms**, and none survives the both-halves requirement.

**The calibration earned its keep on `dte`,** which is the one that looks like a finding:

| `dte` quintile | alert | control | gap |
|---|---|---|---|
| q1 (shortest) | **−0.35%** | +6.29% | −6.64pp |
| q2 | +0.36% | +11.20% | **−10.84pp** |
| q3 | +6.35% | +8.03% | −1.67pp |
| q4 | +4.17% | +7.88% | −3.70pp |
| q5 (longest) | **+7.63%** | +8.05% | **−0.43pp** |

The alert's own expectancy climbs monotonically with tenor while the control's stays flat, and
q2's gap is more than twice the book average. **It does not clear its own calibrated bar**
(`S_worst` 0.472 vs p95 0.497) and it clears in the early half only. Quote it as *suggestive and
not distinguishable from noise by the pre-registered bar* — this is precisely the kind of
eyeballed concentration the X7 method exists to discipline. Note also that q2's −10.84pp is
partly the **control** having its best cell there, not only the alert having its worst.

### 24d · Q3 — does the inverse carry information? **NULL, and it fails informatively.**

A refusal rule was fitted on a decide half (rank bins by gap, refuse the worst, cap 30% of
trades) and applied to the untouched measure half, **both directions**:

| direction | feature selected | refused | measure-half improvement |
|---|---|---|---|
| early decides → late measures | `dte` | q2 | **−0.0977pp** |
| late decides → early measures | `iv` | q3 | **−0.7774pp** |

**Both refusals make the measure half WORSE**, and the two directions select **different
features** — session 7's LOO pattern and session 11's ML-combiner pattern, for the third time.

The sharpest cell: **`iv` q3 is the worst bin on the late half (−7.98pp full-sample) and nearly
the best on the early half (−1.57pp against a −5.43pp baseline).** The "worst part of the book"
does not stay the worst part of the book.

**Q3b — the instrument inverse — is arithmetic and carries no verdict, by construction.** The
anti-signal is **relative to the control, not absolute**: the alert book's own expectancy is
**positive** (+3.27%/trade), so mechanically reversing it is negative before any cost, and the
round-trip spread is paid on top. **You cannot short the gap.** The honest statement is that this
is a reason not to pay for the alert, not a tradeable short.

### 24e · Three defects found and reported

1. **`iv_rank` is wired and 0.0% populated on BOTH books** — a COVERAGE-RULE-class defect. It is
   excluded for having **no values**, not for scoring badly. Owner: whoever populates alert
   features.
2. **`opt_right` and `horizon` are CONSTANT: the banked options book is 100% calls and 100%
   `swing` horizon.** Their `S_worst` is exactly 1.0 and so is every null draw, so they can never
   clear. They are flagged `degenerate` rather than reported as failures — *"did not clear"*
   would otherwise read as evidence about calls versus puts in a book that contains **no puts**.
   Every options claim this project makes is about long calls at swing horizon only.
3. **The alert label vocabulary is PARAMETERISED** — `Low IV 14%` … `19%`, `Volume surge 1.5x` …
   `1.9x` — so one concept becomes many near-duplicate arms. The registered definition is
   **kept** (normalising it now would be a post-hoc degree of freedom, and is a NEW registration),
   and the **trial cost is corrected upward: 32 arms, not 17.** Understating `N` overstates
   significance, so the correction runs against this register's own result.

### 24f · A defect in my own repair, caught by a test before any verdict was read

The first full run selected `labels:Uptrend` in both Q3a directions and **refused nothing**
(+0.0000pp). `S_worst` is mechanically ≈1.0 for a lopsided two-bin feature, and `Uptrend` sits on
**98.5%** of the book, so its only negative-gap bin was larger than the 30% cap. That is the
selection rule finding an artefact of its own statistic, not a null result.

The fix restricts Q3a's pool to features that can actually **express** a refusal. **My first
version of that predicate tested bin *weights* only, and was wrong** — the live failure is not
"every bin is too big", it is "the only bin with a *negative gap* is too big" (the 1.5% bin *is*
small enough; it simply has a positive gap). A test caught it. The predicate now reads decide-half
gaps, which is legitimate — that is what a decide half is for — and **the measure half is never
consulted**. Both corrections are recorded as amendments §9 of the register, appended not
rewritten.

### 24g · Expectations, scored

**2 right, 1 wrong** of three scored (two were arithmetic and not scored).

* **E1 DIFFUSE (65/35) — RIGHT.**
* **E3 the inverse fails out-of-sample (70/30) — RIGHT.**
* **E4 no cut of the alert book loses money outright (55/45) — WRONG.** **17 of 100 bins have
  negative alert expectancy**, and they are the widest-spread, least liquid ones:
  `entry_spread_pct` q5 **−7.41%**, `pit_median_spread_pct` q5 **−5.53%**, q4 −4.38%. Economically
  sensible — that is the cost bill — and the one place a *refusal* rule still looks worth a
  separate registration.

---

## 25 · `O12` — fractional Kelly and ruin. **NOT USABLE, and the halves agreed.**

**The caveat is part of the item, not a footnote: Kelly needs an edge that is real, and R2 says
this entry is dead.** Every fraction below is conditional on a distribution already shown to be
worse than random entry on the same names. **None of it is a sizing recommendation for real
money.**

### 25a · The distribution, and one number in the brief that does not reproduce

n **3,870**, mean **+3.2702%**, median **−52.22%**, min **−101.44%**, max **+782.31%**.
**Hit rate 35.27%.** The task brief said 37%; **that does not reproduce on either book** (35.32%
as-published). The measured value is used throughout.

**The minimum below −100% is correct accounting, not a bug** — checked, not assumed: DHR
2016-06-30 paid $90.00 of premium and lost $91.30, the difference being commission. 4 rows
(0.10%). It does have a consequence: **`f` is hard-bounded below 1/1.0144 = 0.98576**, because
`log(1 + f·R)` is undefined at and above it. Arithmetic, not a finding.

### 25b · Q1 — is `f*` a usable number? **NOT USABLE, but not for the predicted reason.**

| | value |
|---|---|
| `f*` full sample | **0.0403** |
| `f*` early / late | 0.0515 / 0.0293 |
| half ratio | **1.758** — **clears** the pre-committed 2.0 |
| month-block bootstrap CI95 | **[0.0000, 0.1001]**, 8.0% of 400 draws at exactly zero |

**The halves agreed and the bootstrap did not.** I predicted (E2, 60/40) that the halves would
disagree by more than 2× and that this would drive the verdict. They agreed at 1.758. The verdict
is **NOT USABLE** because the CI includes zero — **the right answer for the wrong reason**, which
is worth recording as a miss rather than a hit.

### 25c · Q2 — where ruin lives. **The practical headline, and it is brutal.**

Sequential compounding over the book's own rate of **396.9 trades/yr** (9.75-year span), 10,000
month-block-resampled paths per fraction:

| fraction | median terminal | P(drawdown > 50%) | P(terminal < 0.2×) |
|---|---|---|---|
| `f*` = 0.0403 | 1.267 | **0.753** | 0.049 |
| half-Kelly 0.0202 | 1.200 | 0.222 | 0.001 |
| quarter-Kelly 0.0101 | 1.114 | **0.006** | 0.000 |
| 0.10 (2.5× Kelly) | **0.726** | 0.998 | 0.323 |
| 0.25 | **0.003** | 1.000 | 0.749 |

**At full Kelly you accept a 75.3% chance of halving your account to earn a median +26.7% a
year.** And at 2.5× Kelly — not an absurd overbet — **the median outcome is a LOSS on a book with
positive expectancy**. Quarter-Kelly buys almost all of the growth (1.114 vs 1.267) for 1/125th
of the 50%-drawdown risk. **If any fraction of this ever gets used, it is a quarter or less.**

**The concurrency caveat ships inside the payload**, not in prose: the live book holds several
positions at once, so sequential compounding **understates** its drawdown. These are a floor on
the pain, not an estimate of it.

### 25d · Q4 — the sensitivity, and the most useful line in the item

| distribution | `f*` |
|---|---|
| alert book | 0.0403 |
| **random-entry control** | **0.1110** |
| zero-edge (returns demeaned) | 0.0000 ✓ |

> **The random-entry control supports 2.75× the position size the alert book does.**

That is **R2 restated in sizing terms**, and it is a cost the project had not previously
quantified: the dead entry signal costs not only expectancy, but the *size the book can safely
carry*. The zero-edge arm returning exactly 0 is the implementation check the register demanded —
`G'(0) = mean(R)`, so a non-positive mean admits no positive fraction.

### 25e · Q3 — what the live flat sizing implies

Live rule is **flat 1 contract** (`paper_contracts_per_trade`, default 1) plus the alert's own
$1,000 budget veto. At the book's median premium of **$2.57** that is a **$257 stake**:

| account equity | implied `f` | vs Kelly |
|---|---|---|
| $5,000 | 0.0514 | **1.27× — OVER-betting** |
| $10,000 | 0.0257 | 0.64× |
| $25,000 | 0.0103 | 0.25× |
| $100,000 | 0.0026 | 0.06× |

**Flat sizing equals `f*` at $6,371, half-Kelly at $12,743, quarter-Kelly at $25,486.** So the
live book is under-sized for any account above ~$6.4k and **over-sized below it** — the one place
the flat rule is actually dangerous, and it is the small-account case.

### 25f · A conceptual point pinned by test, because it changes what "ruin" means

**At any fraction below the hard bound, literal ruin is unreachable.** A total loss multiplies
wealth by (1 − f), which is strictly positive, so an all-losses path decays geometrically toward
zero **without arriving** — after 10 total losses at f = 0.999 terminal wealth is 1e-30, not 0.
**A ruin study that counted bankruptcies would have reported that this book can never be
ruined.** That is why the register fixed *threshold* metrics in advance. Pinned by
`test_fractional_betting_decays_but_never_literally_ruins`.

### 25g · Expectations, scored

**3 right, 1 right-with-caveat, 1 wrong on its mechanism.**

* **E1 `f*` under 0.10 (60/40) — RIGHT** (0.0403).
* **E3 control `f*` > alert `f*` (75/25) — RIGHT**, and by 2.75×.
* **E6 P(drawdown > 50%) > 0.5 at full Kelly (70/30) — RIGHT** (0.753).
* **E5 flat sizing below `f*` (55/45) — RIGHT for 5 of 6 account sizes**, wrong below ~$6,371.
* **E2 halves disagree > 2× and drive the verdict (60/40) — WRONG.** They agreed at 1.758.

---

## 26 · What I did NOT do, and why

* **Did not re-mine anything.** Both items run on the banked split-clean books; the frozen chains
  were not touched and no fingerprint changed.
* **Did not change the exit policy, the fill model, or any live code path.** `paper_track`'s flat
  1-contract rule is **unchanged** — O12 describes what it implies and recommends nothing.
  Changing sizing on a dead entry signal would be the wrong order of operations.
* **Did not normalise the parameterised label vocabulary.** It would be a better feature set and
  a **new registration**, not a re-run of this one.
* **Did not run a refusal rule on `entry_spread_pct`,** which E4's failure nominates as the one
  cut still worth testing (its q5 loses −7.41% outright). Selecting it now, after seeing the
  table, is exactly the degree of freedom the register forbids. **It needs its own register.**
* **Did not re-run `BACKTEST_RESULTS.json`.** The trial counter is domain-scoped: both items are
  options, equity `N` is untouched at **155**, and the artifact's Deflated Sharpe does not move.

## 27 · Trial cost

**Options `N` 210 → 246** (O13 33 arms including the corrected label expansion, O12 3).
Calibrations — the permutation nulls, the half-splits, the bootstrap — are charged **zero**,
consistent with session 10's HAC floor. `research_log.detail()` verified:
`{'equity': 155, 'options': 246, 'unified': 0, 'infra': 8}`, `rows_malformed: []`.

## 28 · Recommended next step

**`entry_spread_pct` as a pre-registered refusal rule.** It is the only cut in either item where
the alert book loses money **outright** (q5 −7.41%, q4 of the liquidity twin −4.38%), the
mechanism is economic rather than statistical (it is the cost bill), and a refusal rule is
implementable without shorting anything. It must be its own register — and it inherits O13's Q3a
result as a prior, which is a discouraging one.

**Do not act on `dte` q2.** It is the most eye-catching cell in this session and it does not clear
its own calibrated bar.

---

# SESSION 25 — 2026-08-11 — `O21` + `O26`: **the pricer's dividend gap is real, cheap, and deliberately left alone; the bucket floor cannot deliver what its comment promises**

Two ledger items, one session, frozen book, no re-mine, **no live code path changed**. Both
registers were committed **together and ALONE** at **`bf5324c`** — two `.md`, **zero `.py`**.

Both rows were bare in the ledger ("no mention anywhere in the corpus"), so the scope below is
derived rather than inherited, and each register says what it derived and why.

---

## 29 · `O21` — dividends and early exercise. **IMMATERIAL on the measurable part; one door left UNRESOLVED.**

### 29a · The defect is the CALLER, not the model — and that changes what "fix it" means

`blackscholes.bs_price`, `implied_vol` and `greeks` **already take a continuous dividend yield
`q` and handle it correctly** — `exp(-qT)` on the spot leg, `(r − q)` in `d1`. There is nothing
missing from the model.

> **Every caller uses the default `q = 0.0`.** `enrich_chain(..., q=0.0)` is called in exactly
> two places — `options_backtest.pick_contract:313` and `optvrp_run.py:250` — and neither passes
> it.

**Anyone who "adds dividend support to the pricer" is fixing the wrong thing.** Pinned by a test.

### 29b · The scoping fact that decides what could move

**The banked book's P&L comes from QUOTED bid/ask in the frozen chains, never from a model
price.** So the pricer cannot move the recorded expectancy *directly*. It reaches the book
through exactly three doors, measured separately because they have very different strengths:

| door | mechanism | moves P&L? | result |
|---|---|---|---|
| **D1 early exercise** | the sim always SELLS at the bid | yes, model-free | **+0.2002pp** |
| **D2 contract selection** | `pick_contract` targets 0.35 delta computed at `q = 0` | yes | **4.63% of entries — P&L not computable** |
| **D3 derived fields** | banked `iv`/`target_delta` feed O13 and `delta85` | no | IV understated ~0.62 vol points |

### 29c · Exposure is real and widespread. The measured cost is not.

**81.4%** of the 3,870 banked trades sit on dividend payers (median trailing yield **2.02%**, p90
4.28%, max 24.8%), and **2,107 of 3,870 calls — 54.4% — span an ex-dividend date.** So this is
not a corner case.

**D1, measured model-free:** only **34 of 3,870 exits (0.879%)** were booked below intrinsic,
worth **+0.2002pp** of per-trade expectancy against the pre-registered **1.00pp** bar.

**Early exercise is measured as `bid < S − K` and that is deliberate.** The textbook condition
compares the dividend to remaining time value, which needs a model — and would make the answer a
function of the very pricer under test. The inequality needs no vol, no rate and no dividend
estimate.

**Two controls, both run before any figure was quoted:**

| control | result |
|---|---|
| put-call parity vs the stored `underlying_entry` | median rel error **0.00232**, 93.2% within 1% |
| the sim's **own** bars `raw_close` vs `underlying_entry` | median rel error **0.00000**, **100.0%** within 1% |

### 29d · D2 — the door that is NOT resolved, and it is reported as such rather than as zero

> **The `q = 0` control reproduces the banked contract on 3,870 of 3,870 entries — exactly
> 100.00%.** That is what makes the challenger quotable at all.

The corrected pricer selects a **different contract on 179 entries (4.63%)**. And it is **not a
near-substitute**, which makes the unresolved part *more* serious, not less:

* median **|delta gap| 0.129** against a 0.35 target (p90 0.225)
* **93.9% move to a LOWER strike** — the predicted direction, since a positive `q` lowers call
  delta and the selector must go further in-the-money to reach 0.35
* 87.7% keep the same expiry

**Its P&L is NOT COMPUTABLE on the frozen book.** The freeze stores the **full chain only on
ENTRY dates** and just the traded contract thereafter, so a contract the book never held has no
forward price path — the median alternative has **2 chain dates** and only **10.1%** have more
than three. Resolving D2 requires a re-mine, which this session was scoped out of. **It is
recorded as unresolved rather than assumed to be zero.**

### 29e · D3 — and the direction the register got backwards

Ignoring dividends **understates** the solved implied vol by a median **0.00617** (~0.62 vol
points, max 0.0998) and **overstates** absolute delta by a median **0.00668** (max 0.146). The
path study's `delta85` arm moves from firing on **6** trades to **2** of 3,870 — which cannot
disturb its recorded −0.02pp rejection.

**The register predicted a "negative" IV shift and did not state the direction of subtraction.**
Its stated arithmetic was right — at `q = 0` the model price is higher for any given σ, so the σ
reproducing a market mid is lower — but that means the *corrected minus published* shift is
**positive**. Scored as a miss on the label, with the arithmetic confirmed and pinned by a test.

### 29f · The pricer is deliberately NOT changed

Neither clause of the pre-registered materiality bar is met: D1 is +0.20pp against 1.00pp, and no
published verdict changes its relationship to its bar. **Shipping a selection change on an unmet
bar is exactly what the register exists to prevent** — passing `q` into `pick_contract` would
change **which contract the live engine buys on 4.63% of entries**, at a median delta gap of
0.129. That is a construction change, not a bug fix.

**The non-change is PINNED by two tests** that fail if the live selection path ever silently
starts passing a yield — the same discipline session 16 used for the sizing quantity and session
20 for `zscore`.

### 29g · Two defects in my own instrument, both caught before any verdict was read

1. **Spot at exit was first estimated as `max(call_bid + strike)` over the chain.** Parity gives
   `C ≥ S − K`, so every `bid + K` is an **upper** bound on spot and the **maximum** is the
   loosest one available. It inflated intrinsic and reported an early-exercise gain of
   **+5.62pp** on a smoke subset — **eight times** the true figure, and in the direction that
   would have manufactured a material finding. Replaced by put-call parity, an equality.
2. **The parity helper then rejected `put_mid <= 0`** — which discards exactly the deep-ITM-call
   cases early exercise lives in, and scored **zero rows**.

Both are pinned by tests that hold the *direction* of the old error, so neither can quietly
return. Also found and reported: **`options_backtest.BARS_CACHE` is a RELATIVE path**, so it
resolves to nothing from a git worktree and returns an empty bar set rather than an error.

### 29h · Expectations — 4 right, 1 wrong

RIGHT: IMMATERIAL (70/30); <2% of exits below intrinsic (65/35) at 0.879%; selection changing on
<10% (55/45) at 4.63%; `delta85` moving <1pp (75/25) at 0.10pp.
WRONG: the IV shift's stated sign, as above.

---

## 30 · `O26` — the per-bucket floor. **NULL: it stays 30, and that is not a vindication of 30.**

### 30a · The constant states its own purpose, so the test writes itself

`options_tracker.MIN_CLOSED_PER_BUCKET = 30`, with this comment:

> *"Options outcomes are noisy and heavy-tailed: with ten trades a single triple-up decides the
> sign of every statistic. 30 is not a magic number, it is 'enough that one lucky contract cannot
> flip the verdict'."*

That is a **testable property that had never been tested.** The primary statistic is its literal
reading: **`P_flip(n)`**, the chance that removing the **single most extreme** trade flips the
sign of a size-`n` bucket's mean. The trade removed is `argmax |R − mean|`, chosen **without**
reference to which way it moves the mean — removing the *best* trade would build the answer's
direction into its own definition.

### 30b · It never clears the bar, anywhere on the grid

| n | 10 | 20 | **30** | 50 | 100 | 150 | 200 | 300 |
|---|---|---|---|---|---|---|---|---|
| `P_flip` | 0.2226 | 0.2056 | **0.1848** | 0.1672 | 0.1440 | 0.1318 | 0.1206 | 0.1084 |

Nothing on the pre-committed grid reaches **0.05**, on the full sample or on either half, so the
verdict is **NULL and the constant stays at 30**.

**But that is not a vindication of 30.** Going from 30 to 300 — a tenfold increase **no live
bucket could supply** — moves the flip probability only **0.185 → 0.108**. The floor is doing far
less work than its comment implies, and no achievable floor would change that.

### 30c · The secondary is the stronger result, and I checked it against theory

**Half-to-half sign agreement is a coin flip at every bucket size tested:**

| n | 30 | 100 | 150 | 300 |
|---|---|---|---|---|
| measured agreement | 0.4942 | 0.5098 | 0.5212 | 0.5482 |
| **predicted in closed form** | **0.5059** | — | **0.5289** | **0.5561** |

**That agreement with first principles is the control.** The book's own moments — mean **0.0327**,
per-trade sd **0.9251** — predict the whole curve without any simulation, and the simulation
reproduces it. This is not a resampling artefact.

> **A bucket would need roughly 6,148 trades before its two halves would agree on the SIGN of
> expectancy 95% of the time.** The entire banked book is **3,870**. The largest live bucket
> (large-cap) is **2,058**; mega 994, mid 774, **small 44**.

**So per-bucket expectancy on this book is essentially unmeasurable at any floor.** That is a
third independent corroboration of R2 and O13 rather than a new claim — the book is too noisy to
support subgroup statements, and the floor was never the thing standing in the way.

### 30d · Nothing ships, and nothing could

`MIN_CLOSED_PER_BUCKET` is **untouched at 30**. **Zero live buckets change status.** The item
cannot change live trading behaviour in any case: raising the floor only makes the project *more*
conservative about which subgroups it will read.

### 30e · Expectations — 2 right, 3 wrong

RIGHT: `P_flip(30) > 0.15` (70/30) at 0.1848; the secondary being weaker than the primary
(55/45), and by a wide margin.
WRONG: a floor in the 75–150 range (70/30) — there is none on the grid at all; a RAISE verdict
(60/40) — it is NULL; at least one bucket losing `enough_to_judge` (65/35) — zero did.

---

## 31 · What I did NOT do, and why

* **Did not change the pricer, `pick_contract`, or `MIN_CLOSED_PER_BUCKET`.** No live code path
  moved this session. Both non-changes are pinned by tests rather than left implicit.
* **Did not re-mine.** Both items were scoped to the frozen book, which is exactly why D2's P&L
  is reported as unresolved instead of estimated.
* **Did not re-stamp any derived data.** The register makes re-stamping conditional on the
  materiality bar being met, and it was not.
* **Did not extend O26's `n` grid** past 300 to hunt for the crossing point. The grid is fixed in
  the register and extending it after seeing the curve voids the item. The closed-form
  extrapolation (~6,148) is reported instead and labelled as such.
* **Did not touch O10 / O18**, per the task: they want O14's tick data, which is still collecting.

## 32 · Trial cost

**Options `N` 246 → 248 — one trial each, and O21's charge was CORRECTED UPWARD mid-session.**
It was first charged **zero**, on the reasoning that a correctness measurement against a
pre-committed bar is a `FIXED`-class row. **Another lane's research-page suite rejected that**:
the log schema requires every non-`FIXED` row to charge at least one trial, and this row is not
`FIXED` because **nothing was repaired**. It had a pre-committed bar and returned a verdict
against it, so it is a trial. The correction runs against my own result, which is the right
direction — understating `N` overstates the significance of every DSR-gated claim in the project.
**The gate caught a trial-accounting error that no test of mine would have.**
`research_log.detail()` verified: `{'equity': 155, 'options': 247, 'unified': 0, 'infra': 8}`,
`rows_malformed: []`. **Equity `N` untouched**, so `BACKTEST_RESULTS.json` needs no re-run.

## 33 · Recommended next step

**Re-mine the 179 alternative contracts and close D2.** It is the only door either item left
open, the substitution is large (median |delta gap| 0.129, 93.9% to a lower strike), and it is
the one route by which the dividend omission could still turn out to matter for the headline. It
needs a re-mine and therefore its own session — and, if it does move the book, its own
pre-registration, because at that point the pricer change becomes a construction change with a
measurable consequence rather than a tidy-up.

**Do not raise `MIN_CLOSED_PER_BUCKET`.** O26 says the lever does not work; the useful response
is to stop making per-bucket expectancy claims on this book, not to pick a bigger number.

---

## 34 · `O10` + `O18` — tick-flow execution. **NO VERDICT: MY OWN VOID CONDITION FIRED, AND IT DISQUALIFIED THE ARM THAT WOULD HAVE CLEARED THE BAR.**

Session 26, 2026-08-11. `PREREG_o10_passive_fills.md` and `PREREG_o18_spread_cost.md` were committed
**together and ALONE at `34b0c11`** — two `.md`, zero `.py` — before any measurement code for either
item existed. Frozen book, no re-mine, **no live code path changed**.
`data/free_analysis/O10_O18_TICKFLOW.json`; `scripts/o10_o18_tickflow.py`;
`valuation/edge/tickflow.py`; `tests/test_tickflow.py` (39 tests).

### 34.1 Three scope facts, measured before the registers were written

O14's cache is **exactly the alert-days and nothing else** — 3,884 cached symbol-days, and for the
3,870 split-clean banked entries the **immediate next session is cached for 0 of 3,870** and the
**exit day for 0 of 3,870**. Consequences, both fixed in the registers before anything was run:

* **The live order-working question is NOT ANSWERABLE.** `auto-scan.yml` runs after the close, so
  the live bot's order rests on **D+1**, and D+1 is not in this cache for a single entry. Anyone
  reading this item as *"we measured what the live bot's limit orders fill at"* has misread it.
* **Only the ENTRY leg is coverable** while a round trip crosses the spread twice, so every
  round-trip statement here is an extrapolation and is labelled as one.

What is answerable, cleanly: the **execution environment** of the exact contracts the book traded,
on the day it traded them, measured **quote-relatively** — every quantity is defined against the
NBBO prevailing at the same instant, so nothing needs a decision time and nothing carries
look-ahead. **The join is complete: 3,869 of 3,869 units have the traded contract on tape**, the
one missing alert-day being `BUD` 2024-01-10 (O14's census), which costs **exactly one book row**.

### 34.2 The verdict is that there is no verdict, and why that is the honest outcome

`PREREG_o10 §3 C2` required the behavioural condition-code split to replicate on the full book, and
said in advance that if it did not, `SINGLE_LEG_CODES` is **void** and only the all-codes arm is
reported, **with no verdict**. **It did not replicate, and the cause is a single code.**

| code | share | at-touch (full book) | at-touch (120-entry probe) | verdict |
|---|---|---|---|---|
| 18 | 0.5384 | 0.5873 | 0.561 | touch-seeking, as classified |
| 95 | 0.0544 | 0.8054 | 0.871 | touch-seeking, as classified |
| 0 | 0.0337 | 0.6747 | 0.727 | touch-seeking, as classified |
| 106 | 0.0290 | 0.4374 | 0.450 | touch-seeking, as classified |
| **35** | **0.0494** | **0.2496** | **0.439** | **MISCLASSIFIED — behaves package-like** |
| 125 | 0.1207 | 0.2649 | 0.185 | package-like |
| 130 | 0.1109 | 0.1793 | 0.136 | package-like |
| 131 | 0.0389 | 0.1347 | 0.056 | package-like |

Four of five hold with room to spare. **Code 35 sits below package code 125**, so strict separation
fails and the gate fires. The probe saw 619 of its prints; the full book has 18,922.

**THE VOID IS NOT A TECHNICALITY, AND THIS IS THE PART TO REMEMBER: the arm the register
disqualified is the one that crosses the bar.** The all-codes fallback reads
**NPA 1.0029pp against a 1.00pp bar**; the registered primary reads **0.6318pp**. The register said
in advance that the all-codes arm **credits package liquidity to a single-leg resting order and is
therefore an OPTIMISTIC bound** — and it is exactly the arm that would have manufactured a
material finding. A register that only ever confirms what you were going to conclude is not doing
any work; this one cost a verdict.

**The void did not conceal a crossing, and that is reported because it cuts the other way.** On the
fallback arm the halves read **1.0760 early and 0.9352 late**, so the both-halves condition is not
satisfied there either. That is arithmetic on published numbers, **not a verdict, and it may not be
quoted as one.**

**A PROCESS DEFECT, MINE.** C2 and the outcome statistics were computed in the **same pass**, so I
cannot claim the control was read before the numbers. A gating control must run and be read in a
**separate pass**. That is a flaw in the runner, not in the rule, and the successor register fixes it.

### 34.3 What survives as measurement (no verdict is drawn from any of it)

**O10 — a passive fill is not a free half-spread, and the second term is most of the story.**
At the registered primary cell (rest at the mid, 30-minute horizon), on the void primary arm:

| | gross saving | adverse selection | NPA | fill rate |
|---|---|---|---|---|
| full | +2.4555pp | **−1.8237pp** | +0.6318pp, CI95 [0.5014, 0.7643] | 0.5726 |
| early | +2.6399pp | −1.7240pp | +0.9159pp | 0.5940 |
| late | +2.2593pp | −1.9298pp | +0.3295pp | 0.5500 |

**Adverse selection eats 74.3% of the gross saving.** The naive answer — *"resting at the mid saves
you half the spread"* — is 2.46pp; what is left after the fills you actually get is 0.63pp.

The grid (fill rate / NPA pp), void primary arm:

| level | h5 | h15 | h30 | h60 | rest-of-session |
|---|---|---|---|---|---|
| ask (+1.0) | 0.61 / −0.07 | 0.72 / −0.30 | 0.79 / −0.44 | 0.85 / −0.59 | 0.90 / −0.40 |
| +0.5 | 0.44 / +0.58 | 0.57 / +0.21 | 0.65 / −0.01 | 0.72 / −0.16 | 0.79 / +0.26 |
| mid (0.0) | 0.37 / +1.37 | 0.49 / +0.92 | **0.57 / +0.63** | 0.65 / +0.45 | 0.73 / +1.04 |
| −0.5 | 0.29 / +1.77 | 0.39 / +1.23 | 0.48 / +0.91 | 0.55 / +0.70 | 0.65 / +1.55 |
| bid (−1.0) | 0.26 / +2.13 | 0.36 / +1.65 | 0.44 / +1.38 | 0.52 / +1.19 | 0.61 / +2.14 |

Fill rate is monotone in the limit level at every horizon, as it must be.

**A MEASURED BIAS IN MY OWN INSTRUMENT, REPORTED RATHER THAN LEFT IMPLICIT: the `ask` row is the
instrument's own null and it does not read zero.** By construction the gross saving there is
exactly 0, so NPA should be ~0; it reads **−0.07 to −0.59pp**, because the reference moments that
fail to fill at the ask are precisely the late-session ones with truncated windows. So the NPA
scale carries a bias of that order and the +0.6318pp should be read against it rather than against
a perfect zero. The bias runs **against** the passive arm, so it does not manufacture the null.

**O18 — trades print well inside the quoted spread, and the decomposition keeps the two reasons
apart.** Size-weighted `ρ` = **0.6743** (CI95 [0.6617, 0.6871]) on the void primary arm and
**0.6054** on the fallback; unweighted 0.6737 and 0.5928, so the weighting does not change the
story. In dollars per share, primary arm:

```
q_eod_half 0.1544   ->   q_print_half 0.0999   ->   effective 0.0591
                 availability 0.0545      price improvement 0.0408
```

**Only the $0.0408 is a property of execution.** The $0.0545 availability term is a **selected**
quantity — you only avoid it if you trade when the market is there — and the register forbids
quoting it as a saving. Total apparent overcharge is $0.0953/share = **$9.53 per contract**, of
which only **$4.08** is defensible as price improvement.

**The strongest conditioning is the one nobody registered as most likely: entry premium, not
quoted spread.** `ρ` falls monotonically with premium — **0.778, 0.700, 0.674, 0.626, 0.597** —
with `R_range` 0.1812 against a permutation p95 of 0.0376 (**4.8× the null**) and a negative
Spearman in both halves and both arms. **A cheap option pays nearly its whole quoted half-spread
and an expensive one pays under 60% of it**, which is what a fixed tick on a small premium implies.
`F1` (quoted spread-pct) clears full-sample but not both halves on the primary arm; `F3` (DTE)
clears nothing; `F4` (market cap) clears full-sample only; `F5` (time of day) clears both halves on
the primary arm and not on the fallback.

**`F6` (print size) is DEGENERATE and is flagged rather than reported as a failure** — two of its
five quintile bins are **empty** (`bin_n` `[0, 0, 2771, 2707, 2490]`) because print size is
overwhelmingly one contract, so the 20th and 40th percentile edges coincide. A bin that cannot
exist is not evidence about the thing it would have measured. Same treatment O13 gave `opt_right`
and `horizon`.

### 34.4 The coverage caveat, which is the most important limitation here

**C4 coverage is 0.7162** — 2,771 of 3,869 — clearing the pre-committed 0.70 bar, but only just,
**and the excluded 28% is not a random subsample**:

| | n | median spread% | median mcap | median ATM OI | pit_liquid | median prints | mean P&L |
|---|---|---|---|---|---|---|---|
| included | 2,771 | 0.0571 | $127.8B | 1,575 | 0.901 | 42 | **+5.82%** |
| excluded | 1,098 | **0.0923** | $69.8B | 736 | 0.772 | 5 | **−3.11%** |

The contracts too thin to support a fill study have **62% wider spreads, roughly half the market
cap and half the ATM open interest, and NEGATIVE expectancy**. So **every number above is measured
on the liquid part of the book**, and it is the illiquid part where costs bite hardest — O13
already found `entry_spread_pct` q5 at −7.41%. A cost model calibrated here would be calibrated on
the good half and would understate cost exactly where it matters most.

### 34.5 Two things that must travel with any quotation of this work

* **NOTHING IS ADOPTED. `DEFAULT_AGGRESSION` is untouched at 1.0**, no book was re-banked, no
  published options figure was re-stated, and a test pins the non-change. Both registers fixed that
  routing in advance: a material result is **routed to Don as a policy change**, because changing
  the fill constant would re-price every options figure the project has ever published.
* **CHEAPER FILLS DO NOT RESCUE R2.** The random-entry control is filled by the identical rule, so
  a cheaper entry lifts the alert book and its control together and leaves the **−5.0640pp** gap
  exactly where it is. This is arithmetic, not a prediction, and it is the single most likely
  misreading of the ρ = 0.67 figure.

**The O14 caveat that turned out not to bite, checked rather than assumed:** `HANDOFF_ticks.md`
warns that `quote_timestamp` can lag `trade_timestamp` by hours, which would make the signed
aggression meaningless. On the traded contracts the **median lag is 0.0s and only 0.19% of prints
lag by more than 60 seconds**. Real hazard, negligible exposure here.

## 35 · What I did NOT do, and why

* **Did not change `DEFAULT_AGGRESSION`, any cost constant, or any book.** Pre-committed routing.
* **Did not claim a verdict for either item.** My own C2 gate fired. Amending the code set after
  reading outcomes is void condition 3 in both registers.
* **Did not re-classify code 35 and re-run.** That is the obvious next move and it is precisely
  what the register forbids doing in the same session, because I have now seen the outcome numbers.
  It needs a successor register.
* **Did not extrapolate to the round trip.** Zero exit-day coverage; the exit leg is unmeasured.
* **Did not touch O14's cache, the frozen chains, or the banked book.**

## 36 · Trial cost

**10 options trials, exactly as pre-committed** — 4 for O10 (the non-incumbent limit levels) and 6
for O18 (one per family). **Options `N` 248 → 258. Equity `N` untouched at 155**, and
`BACKTEST_RESULTS.json` needs no re-run because the counter is domain-scoped.

**Charged in full even though neither item returns a verdict**, and the reasoning is worth stating
because it cuts against my own result: session 8's precedent is that **declining to run** keeps the
denominator, but these arms *were* run and measured against their bars. A void verdict does not
refund the search. The fallback arm's 10 further cells are charged at zero because the registers
pre-declared sensitivities as zero-charge and no verdict is drawn from them — the one place the
count is arguable, and it is noted rather than buried.

**Expectations scored 8 right, 3 wrong, 1 split, 1 unscorable.**

| # | expectation | outcome |
|---|---|---|
| O10 E1 | effective < quoted half-spread | **RIGHT** (ρ 0.674) |
| O10 E2 | NPA at the primary cell is MATERIAL | **WRONG** — 0.6318pp against a 1.00pp bar |
| O10 E3 | adverse selection eats ≥ 40% of the gross saving | **RIGHT** — 74.3% |
| O10 E4 | fill rate at the primary cell ≥ 0.50 | **RIGHT** — 0.5726 |
| O10 E5 | fill rate monotone in the limit level | **RIGHT** at every horizon |
| O10 E6 | the package arm shows a HIGHER fill rate | **RIGHT** — 0.6097 vs 0.5726 |
| O18 E1 | ρ < 1 | **RIGHT** |
| O18 E2 | WARRANTED in ≥ 1 family | **UNSCORABLE** — no verdict; both arms would have said yes |
| O18 E3 | F1 has the largest `R_range` | **WRONG** — F2 does, by 4× |
| O18 E4 | ρ falls as the quoted spread widens | **SPLIT** — right in direction (Spearman −0.087) but it fails both-halves |
| O18 E5 | F5 clears in both halves | **RIGHT** on the primary arm, wrong on the fallback |
| O18 E6 | size-weighted and unweighted ρ agree in direction | **RIGHT** — 0.6743 vs 0.6737 |

## 37 · Recommended next step

**Two items, in this order.**

1. **A successor register with the corrected code set, and the gate read in a separate pass.**
   Code 35 belongs with the package group on its measured behaviour; the fix is one constant. The
   successor must (a) commit the corrected set **before** any outcome is recomputed, (b) run C2 and
   **read it** before the outcome statistics exist, and (c) inherit this session's numbers as a
   disclosed prior. It is cheap — the extract is cached, so a full re-analysis is about 90 seconds.
   Expect it to land between the two arms measured here, i.e. **near but probably under the 1.00pp
   bar**, which is why it needs a register rather than a re-run.

2. **The genuinely valuable data item: pull tick flow for EXIT days and D+1.** Everything unresolved
   here is unresolved for the same reason — the cache has only alert-days. D+1 makes the **live**
   order-working question answerable for the first time; exit days make the **second half of the
   round trip** measurable, which is where the cost model is currently pure assumption. O14's lane
   has the cost model for this: roughly the same again as the first pull.

**Not recommended: acting on ρ = 0.67 to lower the cost line.** It is measured on the liquid 72% of
the book, covers one leg of two, and carries no verdict. That is three reasons, any one of which is
enough.


## 38 · `O3` + `O4` + `O5` — the surface-anomaly family. **ALL THREE NULL — and the headline is that the prior lane's one suggestive result REVERSES ITS SIGN when the instrument is fixed.**

**One register, three arms, committed ALONE at `d2aa5f9`** — one `.md`, zero `.py`, a strict git
ancestor of every measurement commit. Frozen book, no re-mine, **no live code path changed, nothing
adopted.**

### 38.1 · The scope fact that comes first: these were already tested once, and rejected

**This is not a fresh question and it is charged as a second look.** `64955ef` (now on `main`)
shipped `valuation/edge/options_xsection.py` and tested **all three characteristics with the
published sign declared before any sort**, returning **REJECT — nothing clears the gate, one
characteristic sorts backwards**. `HANDOFF_free_analysis.md` audited that run and concluded O3, O4
and O5 *"should be considered answered by that same run, not re-opened separately."*

**The sole justification for re-opening is a deviation that lane declared in its own write-up and
never closed:** it used a **straddle**, which is delta-neutral **only at inception**. It accumulates
directional exposure immediately, so its return variance is dominated by the underlying's move —
exactly the variance Cao–Han's daily-rebalanced hedge removes. **This register changes the
INSTRUMENT and nothing else that can be held fixed:** A1 reuses that lane's own `idio_vol` values
and the panel's own strike and expiry, so it differs from the published rejection **in the
instrument alone**.

**The power argument held, and it is the reason the re-run was worth its trials.** Delta-hedged
return dispersion is **sd 0.0303 against the straddle's 0.9055 on the identical events — a 30-fold
reduction** (E6, predicted at 80/20, right by a wide margin). Every arm's |t| rose against its
straddle counterpart (E2, 75/25, right on all four comparisons).

### 38.2 · A second scope fact, measured: the frozen chains named in the task cannot do this

The task named the frozen chains as the instrument. **They cannot support a cross-section, and this
was measured before the register was written.** The freeze holds a **full chain only on the banked
book's ENTRY dates** — median **1** full-chain name per date, maximum 17, and **0 of 2,498 dates and
0 of 120 month-ends** reach the ~20 names a quintile sort needs. **The substitution is therefore
forced and is disclosed in §1 of the register rather than quietly made:** the panel is the prior
lane's EOD-chain panel, and the freeze is used for nothing here.

### 38.3 · The three arms

Panel: **3,373 formation events, 3,323 priceable** (refusals: 43 unpriceable, 7 no-life), **117
formation dates, median 25 names per date** — the register's own void condition (fewer than 50 dates
or fewer than 15 names/date) **did not fire**. Bars are each arm's **own within-date label
permutation p95**, never the conventional 2.0.

| arm | n | monotonicity (bar 0.6) | LS mean | LS t | own p95 | verdict |
|---|---|---|---|---|---|---|
| **A1 — O3 `idio_vol`** | 3,289 | −0.1717 | +0.006043 | 2.5158 | 2.016 | **NULL** |
| **A2 — O4 `exp_idio_skew`** | 3,154 | −0.0380 | +0.004795 | 1.9143 | 1.9229 | **NULL** |
| **A3 — O5 `vol_of_vol`** | 3,318 | −0.0690 | +0.006299 | 2.9703 | 1.9459 | **NULL** |

**EVERY ARM IS NULL ON TWO INDEPENDENT LEGS, WHICH IS WHY NOTHING TURNS ON ANY SINGLE BAR.**
Monotonicity misses 0.6 by three- to fifteen-fold in **both halves of all three arms**, and the
both-halves *t* leg fails independently: A1 clears early (2.2884 vs 2.0508) and **fails late**
(1.1509 vs 2.0122); A3 **fails early** (1.8189 vs 1.8877) and clears late (2.5231 vs 1.9431); A2
clears early (2.2219 vs 1.9608) and fails late (0.4201 vs 1.9201). **The two arms that clear
full-sample fail in opposite halves** — session 7's LOO pattern again.

**A2 misses its own bar by 0.0086 of a *t*.** Recorded a **NULL**, not rounded into a pass
(`RUN_RULES` A6). It is the narrowest miss in the register and it changes nothing, because A2 also
fails monotonicity in both halves and the late-half *t* by 1.5.

### 38.4 · The finding: the published contradiction does not survive the instrument

**This is the part worth carrying.** On the straddle, `idio_vol` sorted at monotonicity **+0.9 with
LS mean −0.0770 and t −1.2142** — flagged by that lane's own machinery as
`contradicts_published_sign`, and the single most suggestive result in its run. **On the
delta-hedged instrument, the same characteristic on the same panel sorts in the CONFIRMING
direction: mean +0.006043, t +2.5158.**

**Both readings are now unquotable as settled.** The confirming ordering here is far too weak to
clear the bar, so **O3 is NULL** — but the prior **CONTRADICTS** reading is an artefact of an
instrument that lets the underlying's move dominate, and **should not be quoted as a finding
either**. E3 predicted the contradiction would repeat, at 60/40, and was **wrong**.

**Mechanism worth carrying:** `idio_vol` is within-date rank-correlated **+0.8444** with the
option's own ATM implied vol, so A1 is close to a **pure implied-vol sort** — high idio-vol means
expensive option, which is Cao–Han's own premise.

**The instrument behaves as the literature says it should, which is corroboration it is real rather
than a bug:** mean delta-hedged gain **−0.0072**, and **every quintile of every arm is negative** —
the volatility risk premium stylised fact, reproduced without being targeted.

### 38.5 · A diagnostic run after the arms were read, labelled as such, carrying no verdict

**The three arms share a shape the register did not anticipate: Q5 is the WORST bucket in all three,
while Q1–Q4 are unordered.** That is precisely how a significant long-short coexists with near-zero
monotonicity. **Both obvious explanations are REFUTED, and refuting them is the useful part:**

* **Not one effect wearing three names.** `idio_vol` and `vol_of_vol` are **negatively**
  rank-correlated within date (**−0.2920**) and share only **14.0%** of their Q5 membership
  (`idio_vol`/`exp_idio_skew` +0.2201 and 42.8%; `exp_idio_skew`/`vol_of_vol` −0.1373 and 21.9%).
* **Not an illiquidity artefact.** The liquidity gradient runs in **opposite directions**:
  `idio_vol`'s Q5 is the **most** liquid corner (mean spread 0.0764 against 0.1063 in Q1), while
  `vol_of_vol`'s Q5 is the **least** liquid (0.0980 against 0.0809).

**Why three largely independent sorts all put their worst bucket at Q5 is left OPEN and needs its
own register.** Testing it here would be **the fourth arm the register's own void condition 3
forbids**, and declining keeps the denominator (session 8's precedent).

### 38.6 · A defect reported outside this lane (`RUN_RULES` rule 3)

**In the prior lane's `panel.pkl`, `illiq` and `spread_pct` are THE SAME COLUMN — identical on all
3,373 rows.** That lane's `illiq` was **the only characteristic in its published run with |t| > 2
(2.46)** and is described as a mechanical liquidity control. It is the option's **quoted spread
percentage under a second name**. Not necessarily a wrong definition — a spread *is* a liquidity
measure — but the panel carries two names for one column, and a reader of that run would reasonably
believe two independent things were measured. **Reported, not repaired: not this lane's file.**

### 38.7 · Two defects in my own instrument, both caught before any verdict was read

1. **My first tests asserted a delta-hedged gain of exactly zero while ignoring the financing term
   `−r(C − ΔS)dt`** that the register's own formula specifies. **The model was right and the tests
   were wrong** — fixed by isolating hedge mechanics at `rate=0.0` and adding a test that pins the
   financing term's sign explicitly.
2. **`score_arm` crashed on the disclosed-comparison arms** (`KeyError: 'idio_skew'`), because it
   read `PUBLISHED_SIGNS[key]` unconditionally and those arms deliberately carry no published sign.
   It crashed **after** the three registered arms had printed, so no registered number was affected —
   **proved, not asserted: all three arms reproduce bit-identically after the repair.** The
   comparison arms now compute **no verdict at all** rather than defaulting a sign and discarding
   the answer, which would have left a scored-then-hidden arm in the code.

### 38.8 · Disclosed comparisons — the prior lane's own definitions, on the new instrument

No verdict, zero trial cost. Both are **weaker** than the registered versions:

| comparison | LS t | own p95 | vs the registered arm |
|---|---|---|---|
| `prior_lane_realised_skew` | 1.5805 | 1.9749 | A2's **expected** skew is STRONGER (1.9143) |
| `prior_lane_vol_of_vol_60dte` | 1.1236 | 1.9204 | A3's **tenor-aligned** series is STRONGER (2.9703) |

**E4 was wrong in the informative direction** — it predicted the expected-skew construction would be
weaker than the realised one, and the construction the literature actually specifies is the stronger
of the two. **E5 was right**: tenor-aligning vol-of-vol moves it materially, so measuring it at a
tenor the instrument does not trade **understates it by a factor of 2.6**.

## 39 · What I did NOT do, and why

* **I did not test what drives the shared Q5 pattern.** It is the most interesting thing in the
  file and it would be **a fourth arm**, which §9.3 of my own register forbids. It needs its own
  register.
* **I did not adopt anything, and nothing could have been adopted whatever the result.** §6 fixed
  that before the numbers existed: a CANDIDATE here would be a candidate for **a future book that
  does not exist**, never a revival of the options entry signal and never evidence R2 was wrong.
  All three arms are NULL in any case.
* **I did not re-open R2.** The entry signal is dead; these are cross-sectional characteristics of
  the option surface, a different object.
* **I did not use the frozen chains** the task named, because §38.2 measured that they cannot
  support a cross-section. The substitution is disclosed, not silent.
* **I did not re-mine any data.** Frozen book throughout.
* **I did not edit the prior lane's `panel.pkl` or its results file** despite finding the
  `illiq`/`spread_pct` collision. Reported to its owner instead.

## 40 · Trial cost

**Options `N` 258 → 261**, one trial per arm, **exactly as §8 pre-committed.** Infra untouched at
**10** — the counter is domain-scoped.

**Equity `N` is untouched BY THIS ITEM but now reads 161, not the 158 I measured while running it.**
The `S3` lane landed three equity trials the same day and I merged them before pushing. Recorded
because it is the reusable lesson rather than a footnote: **an equity figure measured during a
session is stale the moment another lane lands, so re-read `by_domain` after the merge and quote
that.** `BACKTEST_RESULTS.json` needs no re-run for this item — the `S3` lane already refreshed it
at its own denominator.

**Charged in full even though all three hypotheses were rejected once already.** A second look at
the same hypothesis with a better instrument is **another chance for the same hypothesis to clear**,
which is exactly what the counter exists to price. Diagnostics (mid-to-mid, 0 bps hedge, the prior
lane's two definitions, the Q5 correlation work) are charged at **zero**: they search nothing and
carry no verdict.

**Expectations scored 4 right, 2 wrong.** Right: E1 (no arm reaches CANDIDATE, 70/30), E2
(delta-hedged |t| larger than the straddle's, 75/25), E5 (tenor alignment material, 50/50), E6
(dispersion well under half, 80/20 — it is **3.3%**). Wrong: E3 (`idio_vol` sorts against the
published sign again, 60/40 — it **reversed**), E4 (expected skew weaker than realised, 55/45 — it
is **stronger**).

## 41 · Recommended next step

1. **Register the Q5 question properly.** Three largely independent — in one pair *negatively*
   correlated — sorts all place their worst delta-hedged bucket at Q5, and neither the
   one-effect nor the illiquidity explanation survives measurement. That is the only live thread
   here, and it must be a fresh register with its own bar, not an arm bolted onto this one.
2. **Fix the prior lane's `illiq`/`spread_pct` collision** before anything else cites that run's
   2.46. Owner: the options-xsection lane.
3. **Not recommended: quoting any arm here as a positive.** All three are NULL on two independent
   legs each. The one durable result is negative-going and belongs in the record as such — **the
   straddle-based CONTRADICTS reading for `idio_vol` does not survive a properly delta-hedged
   instrument**, so that prior finding should stop being quoted too.


## 42 · `O6` + `O7` + `O17` — the earnings-and-surface-selection family. **ALL TEN ARMS NULL — and the two that came closest each failed on exactly ONE pre-committed leg.**

**One register, three items, ten arms, `PREREG_o6_o7_o17_earnings_surface.md` committed ALONE at
`779d42c`** — one `.md`, zero `.py`, a strict ancestor of every measurement commit. Frozen book,
no re-mine, **no live code path changed, nothing adopted.**

### 42.1 · The ledger was wrong about two of these three rows

`VALQUO_LEDGER.md` marked **O6** `src=auto` — *"prose mentions only, no section, no commit"* — and
**O17** `src=auto` — *"no mention anywhere in the corpus"*. **Both false.**
`VALQUO_EDGE_AUDIT.md:964` and `:1150` are full sections naming four rules each. **So every
definition here is QUOTED from the audit rather than invented, which is the opposite of what
`src=auto` would have licensed.** Both ledger notes are corrected in place.

### 42.2 · The scope fact that governs O7 and O17: coverage is systematic, not thin

`bulk.py` warns that EVENTS code 22 gives *"~2.83 times per ticker per year"* against a full
calendar's ~4. **On this book's 186 megacaps that is wrong in the reassuring direction: median
3.96, mean 4.14, and only 0.3% of entries show an entry-to-next gap over 120 days.** The 2.83 is a
repo-wide average over 17,779 mostly thin tickers.

**The real hole is a systematic exclusion. 29 of 186 names have ZERO earnings dates — 388 trades,
10.0% of the book — and every one is a foreign private issuer** (ASML, AZN, BABA, BHP, the Canadian
banks, SHEL, TM, TSM, TTE, UL …) filing 20-F/6-K rather than 8-K. **A filter reading "no date" as
"no announcement" fails open on a systematically non-random, disproportionately non-US tenth of the
book** — the exact failure mode this lane declined to ship once already
(`EarningsCalendar.unknown_means_safe`, §1526).

**Enforced in code rather than intended:** `refuse_within` and `owns_the_event` return **`None` for
UNKNOWN**, `partition` returns the unknown bucket separately so a caller cannot fold it into either
side, and four tests fail if `None` ever collapses to `False`. The unknown count in every O17 arm
is **zero by construction**, because those names are dropped rather than defaulted.

### 42.3 · O6 — all four NULL, and the strongest number in the item is the CONTROL

Entry date, expiry and holding period held fixed; **only the strike changes**; the incumbent is
re-priced under the identical matched-horizon rule. 3,851 events against a 2,000 void floor.

| arm | gain/trade vs incumbent | own random-alternative p95 | verdict |
|---|---|---|---|
| **A1** lowest IV within ±0.05 delta | **+0.074pp** | −11.31pp | **NULL** |
| **A2** lowest IV vs own trailing IV rank | **−3.505pp** | −11.39pp | **NULL** |
| **A3** lowest IV vs the fitted smile | **−11.099pp** | −11.24pp | **NULL** |
| **A4** highest vega per unit spread | **+0.464pp** | −11.39pp | **NULL** |

**THE RANDOM-ALTERNATIVE p95 SITS AT ABOUT −11.3pp, AND THAT IS THE RESULT WORTH KEEPING.**
Switching to an arbitrary in-band contract costs roughly **eleven percentage points per trade**, so
**the mechanical 35-delta rule the audit proposed replacing is already far better than arbitrary
selection.** That is evidence *for* the incumbent, and it was not what the register expected.

**A3 is the audit's own headline suggestion — the ORATS "smoothed market value" idea — and it is
the WORST arm in the register at −11.1pp/trade.**

**A4 is the near miss and fails on ONE leg only:** positive in **both** halves (+0.534pp early,
+0.401pp late) and clearing its own p95 in both — **NULL solely because tail concentration RISES**
(0.041→0.042 early, 0.034→0.043 late) against the audit's own no-increase clause.

**THE MECHANISM, and it invalidates the audit's framing** (diagnostic, no verdict, zero trials):
**the cheapness rules do not hold the trade fixed and improve its price — they change the DELTA.**
Mean |delta gap| against the incumbent: **A1 0.004, A2 0.248, A3 0.310, A4 0.125**, with A3
drifting 0.374 → **0.458** — deeper in the money and materially more directional. So A3's −11.1pp
is an **exposure** effect wearing a cheapness rule's name. The audit argues this *"cleanly separates
which name from which contract"*; on this candidate set **it does not**.

**A corollary that limits A1, stated because it is the arm most likely to be misread:** a delta gap
of **0.004** means the ±0.05 band pins A1 to essentially the incumbent contract. **Its near-zero
gain is close to tautological and is NOT evidence that cheapness is uninformative.**

**PORTABILITY — the pre-registered random-entry control arm, no verdict, zero trials, and the most
useful thing in the item.** The identical four rules on the five-seed random-entry control book
(5,984 events) reproduce the same ordering and nearly the same magnitudes: **+0.057, −4.140,
−9.382, +0.310pp.** So this is a property of **contract selection generally**, not of the dead
alert days — and it therefore carries to any future book.

### 42.4 · O7 — the diagnostic contradicts the published sign, and the backtest is dead

**Coverage 0.4459** (6,013 of 13,484 events), which **clears its own pre-committed 0.40 floor**, so
B2 is *not* coverage-bound and carries a verdict.

* **B1 — RICH, contradicting Gao–Xing–Zhang.** Mean implied move **5.4512%** against a mean
  realised move **4.7773%**; difference **−0.6739pp**, month-block CI95 **[−0.8475, −0.5070]**
  excluding zero, and realised exceeds implied on only **35.07%** of events. **On this megacap
  universe earnings options are RICH, not cheap.** Stated as universe-specific rather than as a
  refutation: their sample is far broader and their own conditioners say the effect is strongest in
  **smaller** firms, of which this book has none.
* **B2 — REJECTED decisively.** **−10.340%** per straddle net of four crossings, median −25.468%,
  only **31.73%** positive, **negative in both halves** (−11.435%, −9.335%) with both CI95
  excluding zero. The audit predicted the spread would be brutal; it is — the gross event edge is
  under a percentage point and a straddle crosses the spread four times.
* **A DEVIATION STATED PLAINLY:** the register specified a non-announcement-date permutation null
  for B2 and **it was not computed**, because B2 fails the *positivity* leg of its own conjunction
  in both halves and no null could change the verdict. Reported as a deviation rather than left to
  look like a control that ran.

### 42.5 · THREE DEFECTS IN MY OWN INSTRUMENT — the first is the U1-SPLIT defect class recurring

**All three were found by disbelieving a number, not by a test failing**, and all were fixed before
any verdict was read.

1. **THE SPLIT DEFECT, and it is the serious one.** Option chains are as-traded and unadjusted;
   the bars cache's `close` is split- and dividend-**adjusted** — **NVDA in 2012 reads 0.27 against
   a raw 11.97, a 43× ratio.** Matching an as-traded strike against an adjusted spot picks a
   contract nowhere near the money, and it fails **silently**: the straddle still prices, it is
   simply mostly intrinsic. **Measured against the book's own `underlying_entry` over 1,173 banked
   entries: `raw_close` agrees EXACTLY (median relative error 0.00000, nothing over 5% off) while
   the adjusted `close` is off by a median 10.3% and by more than 5% on 67% of entries.**
   **The first cut reported a mean implied move of 19.57% against a realised 5.26% and a confident
   RICH verdict — an ARTEFACT**, with 2.82% of events sitting more than 20% from the money and up
   to 30× off. Repaired to **`raw_close` for anything touching a STRIKE and adjusted `close` only
   for a RETURN** (an adjusted series cannot manufacture a move when a split lands inside the
   window). **Coverage rose 0.2738 → 0.4459 and the implied move fell to a credible 5.45%.**
   It also corrupted the **O6 control arm** and the **O6b IV-rank history** — though **not** the O6
   alert arm, which used the book's own spot throughout. A control that must stay empty now records
   any raw close disagreeing with the book's spot and **reads ZERO**; three tests pin the
   distinction.
2. **The expiry rule priced the wrong thing.** The first cut took the nearest expiry with DTE ≥ 7,
   which prices the move **to expiry** — often 30+ days — against a realised move measured over
   ~4 days. Repaired to the first expiry strictly **after** the announcement and no more than 45
   days out.
3. **A copy-paste:** B2's confidence interval was the *diagnostic's* bootstrap, so two different
   quantities reported bit-identical intervals.

### 42.6 · O17 — all four NULL, and C4 fails on the retention floor ALONE

3,482 usable trades after excluding the 388 foreign-issuer trades. Null = removing a **random**
subset of the same size, because a filter that removes trades changes expectancy mechanically.

| arm | gain/trade | own null p95 | retention | verdict |
|---|---|---|---|---|
| **C1** avoid ≤5d before | +0.797pp | +0.956pp | 0.8745 | **NULL** |
| **C2** avoid ≤10d | −0.479pp | +1.199pp | 0.8202 | **NULL** |
| **C3** avoid ≤15d | −1.429pp | +1.485pp | 0.7588 | **NULL** |
| **C4** own the event | **+4.686pp** | +2.208pp | **0.5706** | **NULL** |

**AVOIDING THE EVENT GETS MONOTONICALLY WORSE AS THE WINDOW WIDENS** (+0.797 → −0.479 → −1.429pp),
and none clears its own null. **The loser autopsy's IV-crush hypothesis is not merely unsupported —
the data points the other way.**

**C4 IS THE HEADLINE AND IT FAILS ON EXACTLY ONE PRE-COMMITTED LEG.** Gain **+4.686pp/trade**,
**positive in BOTH halves** (+5.748pp early, +3.730pp late), **clearing its own calibrated null in
BOTH** (+3.241pp, +2.941pp) — **NULL solely because retention is 0.5706 against the 70% floor**,
refusing 43% of the book. **That floor was fixed before any number existed and for a stated
reason** — a filter achieving its number by refusing almost everything is a *different product*,
not the one-line rule the audit describes. **The verdict stands and the reason is reported; the
floor is not relaxed to fit the result.**

**THE CONFOUND I EXPECTED TO KILL C4 IS REFUTED BY MEASUREMENT, and that is the diagnostic worth
carrying.** Owning the event necessarily selects **longer-dated** contracts, and O13 already
measured that alert expectancy climbs monotonically with tenor — so C4 could have been a **DTE
filter wearing an earnings filter's name**, the failure mode U7 and S10 both recorded. **It is
not.** The tenor difference is small (mean DTE **60.0** kept vs **56.4** refused), and re-scoring
C4 **within** DTE quartiles leaves the gain positive in **every** bucket: **+6.416, +6.310, +2.138,
+2.711pp**. Tenor itself is strong and independently reconfirms O13 — unfiltered expectancy by DTE
quartile runs **+0.376, −0.877, +6.736, +8.584pp** — but **C4 is not that effect**.

**THE `term_slope` INTERACTION THE AUDIT REQUIRED** (reported, no verdict): the refused share under
the 5-day rule falls from **28.9%** in the bottom `term_slope` tercile to **1.7%** in the top, so
the filter and `term_slope` overlap substantially in *which* trades they touch; in the top tercile
the refused trades actually **outperform** (+13.976% against a kept +9.316%).

## 43 · What I did NOT do, and why

* **I did not relax the 70% retention floor to let C4 through.** It is the one arm that cleared
  every statistical leg, and moving a pre-committed threshold after seeing which arm it blocks is
  the precise thing pre-registration exists to prevent.
* **I did not compute O7-B2's registered non-announcement null**, because the arm fails positivity
  in both halves and the conjunction cannot be rescued. Declared as a deviation.
* **I did not adopt anything.** `pick_contract`, `DEFAULT_AGGRESSION` and every cost constant are
  untouched, and the register fixed that before any number existed.
* **I did not re-open R2.** A CANDIDATE here would have been a candidate for a **future** book that
  does not exist; nothing here is evidence the alert entry works.
* **I did not treat a missing earnings date as "no announcement" anywhere**, and I did not include
  the 29 zero-coverage names in any O7 or O17 arm.
* **I did not repair `bulk.py`'s stale ~2.83 caveat** — it is accurate repo-wide and wrong only for
  this universe. Reported here instead.

## 44 · Trial cost

**Options `N` 261 → 271** — 4 (O6a–d) + 2 (O7 B1, B2) + 4 (O17 C1–C4), **exactly as §7
pre-committed.** **Equity `N` untouched at 161, infra at 10** — the counter is domain-scoped, and
the equity figure is re-read after merge rather than quoted from mid-session.
`BACKTEST_RESULTS.json` needs no re-run.

Charged at **zero**: the random-entry control arm, the `term_slope` decomposition, the tenor and
delta-drift diagnostics, and every C-control — none carries a verdict or can produce a claim.

**Expectations scored 6 right, 1 wrong.** Right: E1 (no O6 arm reaches CANDIDATE), E3 (B1 reads
RICH against the published sign), E4 (B2 negative net of four crossings), E5 (no O17 arm reaches
CANDIDATE), E6 (C4 beats C1–C3 in point estimate — by a wide margin), E7 (the `term_slope`
interaction is material). **Wrong: E2**, which predicted a raw O6 improvement killed by the null —
instructive, because the null sits far *below* zero and both positive arms clear it easily; what
kills A4 is the **tail clause**, not the null.

## 45 · Recommended next step

1. **C4 deserves its own register as a CONSTRUCTION rule, not a filter.** It is the only arm in
   three sessions to clear both halves and its calibrated null, its tenor confound is measured and
   refuted, and it fails only a threshold written for a different kind of rule. A register that
   treats "expiry must span the next announcement" as a **contract-selection constraint** — where
   refusing 43% of candidate days is normal rather than disqualifying — is the honest way to ask
   the question. It inherits this session's numbers as a disclosed prior.
2. **Re-check every other options result that used the bars cache for spot.** The split defect was
   silent, and this lane found it only because an implied move of 19.6% was too large to believe.
   Anything matching an as-traded strike against `close` rather than `raw_close` is suspect.
3. **Not recommended: any cheapest-on-surface variant.** Three of four rules lose money, the worst
   is the audit's own headline suggestion, and the diagnostic shows why — on this candidate set a
   cheapness criterion cannot change the contract without changing the delta.
