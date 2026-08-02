# Porkbelly — Cowork Intake Review

**Date:** 2026-07-26
**Scope:** full read of `quant_bots/` (106 files, ~17.2k LOC), `screener/`, `options_backtest/`, plus `HANDOFF.md`.
**Method:** read every module; ran both test suites; verified each finding below by executing the code or grepping the exact call sites. Nothing here is inferred from the READMEs.

---

## 0. The one-paragraph version

The architecture is genuinely good. The signal layer is cleanly decoupled from the data layer, which means the Sharadar swap is much easier than it could have been. The Sharadar purchase is the *correct* purchase for what you want to do.

But there are **four bugs that corrupt data rather than crash**, and three of them are running right now on the Oracle box. The most important one means **the momentum and reversion equity curves you've been patiently accumulating are wrong** — not slightly, structurally. Building a Sharadar backtest on top of the current strategy code would produce a high-fidelity measurement of code that doesn't behave the way the design says it does.

Test suites pass — 82 and 172, exactly as the handoff claims. They pass because they're unit tests of pure functions, and every bug below lives in the wiring *between* correct units. That's not a knock on the tests; it's the specific blind spot to close.

---

## 1. Verification of handoff claims

| Claim | Status |
|---|---|
| 82 monorepo tests, 172 options tests | ✅ Confirmed, both pass clean |
| Momentum: 12-1 ranking, long 30 / short 30 | ✅ Confirmed in code |
| Trend blends 63/126/252-day lookbacks | ⚠️ Confirmed, but the 252 leg is silently dropped at exactly 252 bars (§3.6) |
| Reversion: 21d z-score, \|z\| ≥ 1.0, 20/20 | ⚠️ Parameters confirmed; the \|z\| gate does not do what it implies (§2.2) |
| Regime gate on momentum + reversion, not trend | ✅ Confirmed — and the reasoning in the handoff is sound |
| Vol target 10% | ⚠️ The constant is 10%; realized will be ~3-6% (§3.1) |
| Options SIM unit bug is fixed | ✅ Confirmed fixed and locked down by tests |
| Sharadar gives no options IV | ✅ Correct. Options bot stays on the index proxy |
| Nasdaq Data Link still the right platform | ✅ Confirmed alive and canonical as of July 2026 |

---

## 2. Critical — data-corrupting, live right now

### 2.1 Momentum & reversion never close positions in SIM

`momentum/orchestrator.py:161-163` (and the identical block in `reversion/orchestrator.py:145-147`) builds the price map from the *current selection only*:

```python
last_prices = {}
for s in selection.longs + selection.shorts:
    last_prices[s.symbol] = s.last_price
```

A name that dropped out of the top/bottom-30 is by definition not in `selection`, so it has no price. `core/sim_execution.py:56-58` then does:

```python
price = last_prices.get(o.symbol, 0.0)
if sign == 0 or price <= 0:
    logger.debug("Skipping sim fill for %s (no price/side)", o.symbol)
    continue
```

The exit order is generated correctly by the portfolio layer and then **silently dropped at DEBUG level**. Verified by execution:

```
planned: [('NEWNAME','buy',100,'add long'), ('OLDNAME','sell',100,'exit (not in target)')]
filled:  [('NEWNAME','buy',100)]
after:   {'OLDNAME': 100, 'NEWNAME': 100}
```

It compounds. `SimPortfolio.total_equity` (`core/sim_portfolio.py:161`) falls back to `prices.get(sym, h.avg_cost)`, so every stranded position is **marked at its entry cost forever** — P&L frozen at exactly zero. Positions accumulate without bound across rebalances; gross exposure drifts past every cap.

**Consequence:** every equity curve, Sharpe, vol, and correlation number for momentum and reversion is wrong, and has been since they started. The correlation tracker — the entire point of the SIM pilot — is reading corrupted input for 2 of 4 bots.

Trend is accidentally immune: its `last_prices` is built from all signals over a fixed 25-name basket, so it always covers held names.

The same defect exists in the backtester at `core/backtest.py:175`, which passes `last_prices` two lines after building the correct `mark_prices`:

```python
mark_prices.update(last_prices)                     # mark_prices HAS the held names
...
_apply_plan_to_sim(sim, plan.orders, last_prices)   # passes the wrong dict
```

**Fix:** one line in each orchestrator (extend `last_prices` to cover held symbols), one word in the backtester. Then restart the SIM curves from zero — the accumulated history is not salvageable.

### 2.2 Reversion shorts oversold names in a selloff

`reversion/signals.py:154-160` applies `min_abs_zscore` as a **pool filter**, then splits by *rank*, not by sign:

```python
usable = [s for s in scores.values()
          if s.usable and abs(s.zscore) >= config.min_abs_zscore]
usable.sort(key=lambda s: s.score, reverse=True)
longs  = usable[: config.long_count]
shorts = usable[len(usable) - config.short_count:] ...
```

Nothing requires shorts to have `z > 0`. In a market-wide drawdown where every name is oversold, the bot goes long the 20 most oversold and **shorts the 20 least-oversold — names it has itself flagged as oversold**. Verified with 50 names all at z ∈ [-3.65, -1.20]: all 20 shorts had negative z.

This fires precisely in the fat-left-tail scenario the module docstring warns about, and doubles the loss instead of hedging it.

**Fix:** partition by sign before slicing — longs from `z ≤ -1.0`, shorts from `z ≥ +1.0`, each capped at 20. Accept that some days produce an unbalanced book; that's the honest answer.

### 2.3 Options bot: risk limits do nothing in SIM

`orchestrator/jobs.py:207-221` has no SIM branch:

```python
account_value = self.tradier.get_account_value()
positions     = self.tradier.get_positions()
...
risk_result = self.risk.filter_orders(orders=..., account_value=account_value,
                                      current_positions=positions, ...)
```

`is_sim` is checked in exactly two places in the whole options codebase (`jobs.py:256`, `jobs.py:383`) — both *after* this. In SIM the bot places no broker orders, so `positions` is empty forever, every day. Therefore:

- `max_concurrent_positions = 10` sees 0 open → accepts 10 new spreads
- `max_positions_per_ticker = 1` sees 0 → same ticker re-opens daily
- `max_total_deployed_pct = 0.50` sees $0 deployed
- strategy dedup fingerprints are empty → no dedup
- `account_value` is the *broker's* equity, so sim P&L never feeds back into sizing

The only brake is a `spread_id` collision check keyed on `symbol-exp-shortK-longK`, which almost never collides because strikes drift with spot and the 35-DTE target rolls. Net: **the sim book grows by up to 10 spreads/day without bound**, and its equity curve does not represent the risk-limited strategy.

### 2.4 Screener: the largest weight in the model is a constant

```
$ grep -rn "dcf_upside" screener/
scoring.py:54,56,58,148   ← four hits, all inside scoring.py
```

Nothing in `edgar.py`, `pipeline.py`, or `store.py` ever sets the key. `value_score_established(None)` returns `50.0` for every established name, every day.

**The 35%-weight value component of the Established bucket — the single largest weight in the model — is inert.** Established names are effectively ranked on quality/momentum/insider renormalized to 65%. The README lists "DCF-gap value" as a locked design decision; there is no DCF in the codebase.

---

## 3. High — wrong but not corrupting

**3.1 The 10% vol target is unreachable by construction.** `trend/risk.py:91-98` computes `weighted_vol` as the weighted-average *single-name* vol, ignoring diversification entirely. For a 60-name book at 35% single-name vol: `vol_scale = 0.10/0.35 = 0.286`, gross exposure 27%. A 30-long/30-short book at 27% gross realizes roughly 3-6% vol, not 10%. The docstring is honest that this is deliberately conservative — but the effect is that the bots run at a third of intended risk, and every Sharpe/correlation number is computed on a book far smaller than one you'd deploy.

**3.2 The regime gate makes the "dollar-neutral" bots 100% net long.** `selection.shorts = []` then gross-normalizes over the remaining longs to 1.0 → net weight +1.0. Whenever SPY is above its 200d MA (most of the time), momentum and reversion are fully net long, single-sided equity beta. Nothing in the code or README acknowledges this. The `max_net_exposure` cap can't catch it — with `max_gross = 1.0` the net check at `risk.py:114` is dead code.

**3.3 The screener backtest tests a different model than the screener runs.** `run_backtest.py` never imports `scoring.py`. It uses `WEIGHTS = {ey_sn: .30, roe: .10, opm: .10, neg_lev: .10, mom: .20, growth: .20}` — no bucket split, no insider score, no DCF, no gates, no cap ceiling, and `ey_sn` doesn't exist in the live model. Two independent scoring models coexist in the repo. The insider component (20-30% of live weight) has never been backtested at all.

**3.4 The screener backtest universe is the ~300 *largest* US companies.** `all_filers().keys()[:300]` — SEC's file is ordered by market cap descending. That's the exact inverse of the sub-$10B universe the screener targets.

**3.5 `pit_data._pit_point` mixes quarterly and annual figures.** It selects by latest `end`/`filed` and never filters on period duration, so after a 10-Q lands it returns a *quarterly* net income — while `revenue` comes from `_pit_annual` which correctly restricts to FY. Verified: `opm` drops 4× the moment a 10-Q lands, no change in the business. This corrupts `ey`, `roe`, `opm` — 3 of 6 factors, 50% of backtest weight. **Sharadar's `dimension='ART'` fixes this for free.**

**3.6 Trend's 252-day lookback is dropped at exactly 252 bars.** `signals.py:114` guards `if lb < n` while `min_bars_required = 252`. Verified: at n=252 the blend uses only [63, 126]; at n=253 it uses all three. Affects newly-listed names and the first days of every backtest.

**3.7 A missing quote on one option leg triggers a spurious profit-close.** Both `portfolio.py:291` and `jobs.py:500` guard with `and`, not `or`:
```python
if short_ask <= 0 and long_bid <= 0: continue
```
Short leg fails to quote (`0`) but long leg quotes at `0.20` → close cost = **−$20/spread** → `pnl_pct > 1.0` → `CLOSE_PROFIT`. In live this fires a real closing order; in SIM it *realizes* phantom cash into the equity curve. Missing quotes on illiquid long legs are routine.

**3.8 The forward-return tracking loop was never written.** `store.update_returns`, `prices.benchmark_return`, `config.BENCHMARKS`, `config.TRACK_HORIZONS_DAYS` all exist; nothing calls them. `ret_7/ret_30/ret_90` stay NULL forever, and `run_review` hands an all-NULL table to Claude for self-review (the only guard is a row count, and rows exist). The entire track-record / self-improvement loop is unwired.

**3.9 The screener health gate aborts on a single feed error.** `if feed_errors > 0` across ~13,000 tickers × 2 feeds. Zero errors is not achievable. Guaranteed failure on run #1. Also `yfinance` is not in `requirements.txt` despite being the documented price fallback, and the model IDs (`claude-opus-4-8`) need re-verification — a bad ID raises *unguarded* mid-run, after Established has posted to Discord but before Speculative and before spend is recorded.

---

## 4. Sharadar — what I confirmed

Full technical reference is in `SHARADAR_REFERENCE.md`. The decision-relevant parts:

- **Nasdaq Data Link is alive and canonical.** Not sunset, not moved. `https://data.nasdaq.com/api/v3/datatables/SHARADAR/{TABLE}.json`. Sharadar is not sold direct — your Nasdaq key is the right and only credential.
- **Bundle = 12 tables:** `SF1, SEP, SFP, TICKERS, DAILY, ACTIONS, EVENTS, SP500, SF2, SF3, SF3A, SF3B`. Note: there is no `SHARADAR/METRICS`; you're thinking of `DAILY`, whose title is "Daily Metrics."
- **Point-in-time discipline:** use dimensions `ART`/`ARQ`/`ARY` (As-Reported, restatements excluded). Index on **`datekey`**, shifted **+1 day**. `MR*` dimensions are restated *and* set `datekey` to the fiscal period end — two independent look-ahead traps in one field. `calendardate` is a cross-sectional alignment key, never a time index.
- **Prices:** `closeadj` for returns (split + dividend adjusted), `closeunadj` for price-level screens, `close` is split-only. Using `close` for momentum silently understates total return by the full dividend yield. SEP is stocks only; ETFs are in SFP.
- **Survivorship-free confirmed** — delisted tickers retain full history. This is the thing you're paying for and it's real.
- **Join on `permaticker`, not `ticker`** — tickers get recycled and reassigned.
- **Row limits:** 10,000/call with a cursor; the official Python client hard-fails at 1M rows and returns *nothing*. SEP and SF1 both exceed that. Use `qopts.export=true` bulk download (Sharadar's own script does).
- **First call to make:** `SHARADAR/INDICATORS?table=SF1,SEP,TICKERS,ACTIONS,EVENTS,EVENTCODES` — Sharadar publishes its own data dictionary as a table. Resolves ~6 open schema questions in one request.
- **One unknown worth probing on day one:** whether a restatement *appends* a new ARQ row (same `reportperiod`, later `datekey`). If it does, a naive `groupby('reportperiod').last()` reintroduces look-ahead. Test against a known 10-K/A filer; if non-unique, always take the earliest `datekey`.

---

## 5. What the Sharadar swap actually costs

**The easy part (genuinely easy).** Every signal function already takes a bare `list[float]` of closes:

```python
compute_signal_from_closes(symbol, closes, config)      # trend
compute_score_from_closes(symbol, closes, config)       # momentum, reversion
classify_regime_from_closes(closes, config)             # regime gate
```

and every consumer holds an **untyped** `self.tradier`. A duck-typed adapter exposing `get_history(symbol, start, end, interval) -> [{"date": iso, "close": float}]` drops into all five call sites with zero changes to strategy code. That's the whole swap for signal generation.

**The real work, in four places:**

1. **`UniverseBuilder` has no as-of concept.** `build()` takes no arguments and hits the live Nasdaq screener. This is where the bias is manufactured, and it's worse than "today's universe": it filters on *today's* price ≥ $20 and *today's* cap ≥ $2B, sorts by *today's* market cap, then takes the top 150. A 2021-2024 momentum backtest trades the 150 largest companies as of today, throughout history — pre-selecting the winners of the period being measured. This needs a genuine point-in-time rewrite against `TICKERS` + `DAILY`, not an adapter.
2. **`PriceHistory.fetch` does one HTTP call per symbol** with a 0.1s floor, and `price_on`/`closes_up_to` are O(n) linear scans called per-symbol per-day (~10⁸ ops at 150 symbols × 750 days). Sharadar returns the whole panel in a few bulk calls — preserving the per-symbol loop throws away the main advantage.
3. **`closeadj` vs `close`.** Every signal here is a ratio of two closes at different times. Tradier history is already split-adjusted so this bug can't exist today; it's very easy to introduce.
4. **Delisting returns.** `forward_return` currently returns `None` when the window runs off the end of the price series — which would *drop delisted names and reintroduce the exact survivorship bias you're paying to remove.* Needs `TICKERS.lastpricedate` + `ACTIONS`.

**Also missing:** there is no reversion backtest at all. `run_backtest.py` supports `trend` and `momentum` only; `--bots reversion` silently does nothing and prints "Backtests complete."

**And the backtest doesn't test what trades:** the kill switch never fires (`today_pnl_pct` never passed), the regime gate is absent from `backtest_momentum` entirely, and `_apply_plan_to_sim` is a second implementation of `apply_orders_to_sim` that drops slippage. The module docstring's claim that "the backtest tests the same code that trades" is false for momentum.

**The good news on the screener side:** `backtest_engine.py` is the strongest code in the repo — fully implemented factor diagnostics (Spearman IC with t-stats, quantile returns net of costs, top-quintile vs benchmark, OOS split) with an appropriately demanding verdict heuristic. Its panel contract is `date, ticker, composite, fwd_ret, bench_ret` + optional factor columns. **Zero changes needed.** It's a factor-diagnostics module, not a portfolio simulator — no sizing, turnover, compounding, or drawdown. Fine for "does the composite rank-predict returns," which is the right first question.

---

## 6. What Sharadar can validate about the options bot (more than expected)

The handoff says Sharadar does nothing for the options bot. That's right about the *premium* — but wrong about the *risk*, and the risk side is where the real question is:

- **The universe layer is fully testable.** `min_price=$20`, `min_cap=$2B`, `min_volume=500k` need only equity data. SEP + DAILY + TICKERS reproduces it point-in-time and survivorship-free.
- **The earnings-avoidance filter is testable.** `SF1.datekey` proxies the announcement. Measure the empirical 35-day return distribution of names with vs. without an in-window event.
- **The left tail is testable.** A put credit spread's outcome is a function of the *underlying's path* once strike and credit are fixed. With SEP you can measure how often a universe name drops enough in ~10 trading days to blow through a $5-wide spread, and whether the 21-DTE exit actually avoids the worst of the distribution.
- **The highest-value item: portfolio-level correlation.** `risk.py` has no correlation, beta, or sector control anywhere — "10 concurrent, 1 per ticker" is treated as diversification, but 10 put credit spreads are one short-vol/long-beta bet. Equity-only data is sufficient to show whether 10 positions is 10 bets or 1, and to quantify the drawdown the current limits permit in a correlated selloff. The index-proxy backtest can't see this (single position stream). **This is the largest un-modeled risk in the stack.**

Not testable: strike selection, the mid, the bid-ask and OI gates, the credit collected — i.e. the variance risk premium itself. That's the index-proxy backtest's job. The two are complementary, not redundant.

---

## 7. Also worth knowing

- **`options_backtest` cost model is honest and conservative.** ~$10.60/spread round trip (4×$0.65 commission + $0.08/share slippage) against a typical ~$70 credit. The stop gap-through is real — exits book at the actual BS mark, not the 2× cap. I ran it on synthetic GBM with IV pinned at realized vol (zero premium by construction) and got −16.9% / Sharpe −0.40 over 753 trades. **The engine does not manufacture edge.** That's the right property.
- Two things it *doesn't* model that the live bot does: vol-scaled sizing (absent — so it overstates 2020/2022 losses relative to the deployed bot) and `max_contracts_per_spread=10` (uncapped, so it takes larger positions as equity compounds). Also Sharpe has no risk-free subtraction — inflated by ~0.8 at current rates.
- **README drift is significant across all three projects.** Options README says 20-30 delta / 30-45 DTE / IV rank > 30 / dynamic $5-$10 width — actual is 0.20±0.05 delta, 25-50 DTE, ATM IV ≥ 0.25 (not IV *rank*), flat $5 width. `strategy.py`'s own docstring still describes the dead dynamic-width rule. Trend README says 26 instruments; the basket has 25. Screener README marks four modules "built + unit-tested" — there are no test files anywhere in the screener.
- `insider_score` output range is [25, 75], not [0, 100] — `50 + 25·tanh(...)` can't leave that band, so the `np.clip(...,0,100)` is a no-op and the insider component delivers ~half the cross-sectional dispersion its 20-30% nominal weight implies. It also saturates at ~$1M of aggregate buying (1 CEO buy of $250k → 67.6; ten $10M buys → 75.0).
- `t.get("person", id(t))` doesn't handle `person=None` — `dict.get` only returns the default when the key is *absent*, and the EDGAR parser sets it explicitly. Every unnamed filer collapses to one key, so a real 4-person cluster registers as 1 buyer. **Sharadar SF2 fixes this for free** (real `ownername` column) and removes the Form-4 parser, the deprecated firehose endpoint, and the ticker-less-alert bug in `insider_poller.py` in one pass.
- `insider_poller` alerts have no ticker (the parser never emits one), so every alert titles as `?` — and because the throttle keys on ticker with `MAX_ALERTS_PER_NAME_PER_WEEK=3`, **the poller goes permanently silent after 3 alerts per week**, across all companies.

---

## 8. Recommended sequence

**Tier 0 — before any Sharadar work (small, mostly one-liners):**
1. Fix §2.1 (exit orders dropped) in both orchestrators + the backtester. Restart momentum/reversion SIM curves from zero.
2. Fix §2.2 (reversion shorts oversold names) — partition by sign.
3. Fix §2.3 (options SIM risk limits) — feed the sim book into the risk layer.
4. Add integration tests for all three. These bugs are in the wiring between correct units; that's the gap the current suites don't cover.

Rationale: every day the box runs unfixed is a day of unusable correlation data, and the whole SIM pilot exists to produce that data. This is cheap and it's blocking the thing you're already paying for in wall-clock time.

**Tier 1 — Sharadar foundation:**
5. `INDICATORS` call → confirm schemas. Probe the restatement question.
6. Bulk-export SEP + SF1 + TICKERS + SF2 to local storage (DuckDB or Parquet); incremental sync on `lastupdated`.
7. Data adapter with the duck-typed `get_history` interface + a bulk panel loader.
8. **Point-in-time `UniverseBuilder`** — the actual hard part, and the one that fixes the bias.

**Tier 2 — rewire the backtests:**
9. Momentum + reversion (reversion needs building from scratch), on the PIT universe, with the kill switch and regime gate actually wired so the backtest tests what trades.
10. Delisting-return handling.

**Tier 3 — screener:**
11. **Resolve the two-models contradiction first** (§3.3) — decide whether to backtest `scoring.py` as deployed or finish the migration to `cross_sectional.py`. Building a high-fidelity PIT backtest for a factor set production doesn't use is wasted work.
12. Decide what happens to `dcf_upside` — implement it, or drop it and renormalize.
13. Swap `pit_data`'s body for SF1 `ART` (keep the signature), point prices at SEP, fix the universe.

**Tier 4 — optimization, last and guarded:**
14. Walk-forward / out-of-sample from the first commit, not bolted on. Parameters chosen in-sample, evaluated out-of-sample, once. Every result reported with the number of configurations tried.

**Deferred, correctly:** the allocation overlay. It needs real correlation data — which, per §2.1, does not exist yet.

---

## 9. The honest framing hasn't changed

Nothing found here changes §11 of the handoff. At ~$4k in a taxable account, buy-and-hold indexing is still very likely the better wealth outcome, and the tax drag on short-term gains roughly doubles the hurdle. What this project is worth is the education and the portfolio piece — and on that axis, *finding and fixing §2.1 is worth more than any backtest result*. "I found a silent data-corruption bug in my own live system by reading the wiring between tested units" is a better story for an MSF interview than any Sharpe ratio you'll produce.

One thing to add to the honest framing: the Sharadar subscription is a real recurring cost (~$79+/mo) against a $4k account. That's ~2%/yr of the portfolio in data fees. It's justifiable as an education/portfolio expense — it is not justifiable as an investment expense, and it's worth being explicit about which one you're buying.
