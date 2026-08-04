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

# C1 / C2 — in progress

Universe and scorer are rewired and the data pull is running; results appended
when the run completes. C2's premise is already confirmed and is stronger than
the audit states — see below.

---

*Note: `HANDOFF_STATUS.md` has deliberately NOT been overwritten. Several agents
are working parallel lanes against this repo and that file is shared project
state; overwriting it from one lane would clobber the others. This file is this
lane's full report.*
