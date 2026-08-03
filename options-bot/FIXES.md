# Fixes — 2026-07-26

Three data-corrupting bugs, plus regression tests that fail against the old code and pass against the new.

**Test counts changed. If you see the old numbers after a deploy, the old code is still there.**

| Suite | Before | After |
|---|---|---|
| `quant_bots` — `python -m unittest discover tests` | 82 | **106** |
| `quant_bots/options` — `python -m unittest discover` | 172 | **181** |

---

## 1. Exit orders were silently dropped in SIM (momentum, reversion, backtester)

**What was wrong.** Each orchestrator built its price map from the *current selection only*:

```python
last_prices = {}
for s in selection.longs + selection.shorts:
    last_prices[s.symbol] = s.last_price
```

A position that had dropped out of the top/bottom-30 was, by definition, not in the selection — so it had no price. `apply_orders_to_sim()` skips any order it can't price, at `logger.debug`. Exit orders therefore never filled.

It compounds: `SimPortfolio.total_equity()` marks an unpriced holding at `avg_cost`, so every stranded position's P&L was **frozen at exactly zero**, forever. Positions accumulated without bound, gross exposure drifted past every cap, and the equity curve stopped describing the strategy.

Trend was accidentally immune — its price map covers a fixed 25-name basket, so held names are always present.

`core/backtest.py:175` had the same defect: it passed `last_prices` two lines after building a correct `mark_prices`.

**Fix.**
- `RankedSelection` now carries `all_prices` — the last price for *every* scored name, not just selected ones. Free; the data was already fetched.
- New `core.sim_execution.resolve_prices()` backfills, via `get_quotes`, anything still held but no longer scored (e.g. the name left the universe entirely), and **returns what it still couldn't price** instead of swallowing it.
- All three orchestrators route through it. The SIM summary line now reports unfilled orders and unpriced holdings, so a future failure is visible in Discord rather than silent.
- `apply_orders_to_sim` logs skips at **WARNING**, not DEBUG.
- The backtester passes `mark_prices`, and its private `_apply_plan_to_sim` is now a thin wrapper over the shared `apply_orders_to_sim` — the duplicate implementation is how live and backtest drifted apart in the first place.

**Files.** `core/sim_execution.py`, `core/__init__.py`, `core/backtest.py`, `momentum/signals.py`, `momentum/orchestrator.py`, `reversion/signals.py`, `reversion/orchestrator.py`, `trend/orchestrator.py`

**Tests.** `tests/test_sim_exit_integrity.py` — 14 tests. Against the old code: **7 fail**, including `positions accumulated: {'AAA': 200, 'BBB': 400, 'CCC': 250, 'DDD': 333, 'EEE': 285, 'FFF': 222}` after three rotations that should have left two.

---

## 2. Mean-reversion shorted oversold names in a selloff

**What was wrong.** `rank_and_select` filtered on `|z| >= min_abs_zscore`, sorted the whole pool, then took the top N as longs and the **bottom N as shorts**. Nothing required a short to have `z > 0`.

In a market-wide drawdown every name has `z < 0`, so the bottom of the pool is the *least oversold* name — still oversold. The bot shorted names it had itself just classified as oversold, in exactly the fat-left-tail scenario the module docstring warns about, doubling the directional loss instead of hedging it.

**Fix.** Partition by sign *before* slicing. Longs come from `z <= -threshold`, shorts from `z >= +threshold`, each capped at its count.

**The tradeoff, stated plainly:** the book is now lopsided on skewed days — 20 longs and 3 shorts, sometimes 20 and 0. That is the honest answer; there genuinely were no overbought names. A guaranteed-balanced 20/20 book was the bug, not a feature. The orchestrator logs "Broad selloff: long-only this cycle" when it happens.

**Files.** `reversion/signals.py`

**Tests.** `tests/test_reversion_sign.py` — 10 tests. Against the old code: **4 fail**, including a 50-name all-oversold cross-section where the old code shorted 20 names with z between −2.15 and −1.20.

---

## 3. Options bot: every risk cap was inert in SIM

**What was wrong.** `open_job()` always took its state from the broker:

```python
account_value = self.tradier.get_account_value()
positions     = self.tradier.get_positions()
```

In SIM the bot places no broker orders, so `get_positions()` returned `[]` every day, forever. Every cap is computed from that list:

- `max_concurrent_positions = 10` saw 0 open → approved a full book daily
- `max_positions_per_ticker = 1` saw 0 → re-opened the same ticker daily
- `max_total_deployed_pct = 0.50` saw $0 deployed → never bound
- the strategy's fingerprint dedup got an empty set → did nothing

The only brake was a `spread_id` collision — and `spread_id` embeds the strikes and expiration, both of which drift daily as spot moves and the 35-DTE target rolls. So it almost never collided.

**Fix.** New `Jobs.sim_positions_view()` renders the sim book as Tradier-shaped position dicts (two legs per spread, because `_count_open_by_ticker` counts legs and halves). In SIM, `open_job` feeds those to the risk manager and to the dedup, and uses sim equity rather than broker equity. `cost_basis` is set so the leg pair sums to the spread's **true max loss** — which is also how `_sum_deployed_dollars` measures *new* orders, so both sides of the cap comparison are finally in the same units.

Also hoisted the per-order sim reload out of the open loop; it was calling `get_account_value()` once per order and re-saving the book each iteration.

**Files.** `options/orchestrator/jobs.py`

**Tests.** `options/tests/test_sim_risk_state.py` — 9 tests. Against the old code: **3 fail**, including a run that opened **30 spreads over 3 days against a cap of 10**, and a second AAPL spread despite `max_positions_per_ticker=1`.

---

## Deploying this

The curves produced before these fixes are **not salvageable** — a frozen-at-cost position can't be re-marked after the fact, and a book that ignored every risk cap never represented the strategy. Archive them and start clean.

```bash
ssh -i ~/ssh-key-2026-05-29.key ubuntu@141.148.45.115
bind 'set enable-bracketed-paste off'          # type this by hand
sudo systemctl stop trend-bot momentum-bot options-bot reversion-bot
cd ~                                            # unzip from HOME, never from inside quant_bots/
unzip -o ~/quant_bots.zip
cd ~/quant_bots && source venv/bin/activate && pip install -r requirements.txt
python -m unittest discover tests               # want 106
cd options && python -m unittest discover       # want 181
cd ..
python scripts/reset_sim_curves.py --bots momentum reversion options --dry-run
python scripts/reset_sim_curves.py --bots momentum reversion options
cat .env                                        # confirm secrets survived
bash deploy/install_services.sh
systemctl is-active trend-bot momentum-bot options-bot reversion-bot
```

`reset_sim_curves.py` deletes nothing — it moves each book to `data/sim/_archive/<bot>_<timestamp>/`.

**Trend does not need resetting.** Its curve was never affected. Keep it; it's your only continuous history.

Expect the correlation tracker to warn about insufficient overlap for the next few weeks. That's correct, not a bug — momentum and reversion are starting from day zero.

---

## Known issues NOT fixed here

Deliberately out of scope for this pass — see `FINDINGS.md` §3 for the full list and evidence. The ones most likely to bite:

- **The 10% vol target is unreachable by construction.** `weighted_vol` is a weighted-average *single-name* vol that ignores diversification, so a 60-name book runs at ~27% gross and realizes roughly 3-6% vol. The bots are running at about a third of intended risk.
- **The regime gate makes the "dollar-neutral" bots 100% net long.** Suppressing shorts then gross-normalizing over the remaining longs sets net weight to +1.0 — whenever SPY is above its 200-day MA, which is most of the time.
- **A missing quote on one option leg triggers a spurious profit-close.** The guard is `and` where it should be `or`; a zero short-leg quote against a live long-leg bid produces a *negative* close cost and fires `CLOSE_PROFIT`. In SIM it realizes phantom cash.
- **Trend's 252-day lookback is silently dropped at exactly 252 bars** — the blend quietly becomes 3/6-month.
- **High-priced names are silently dropped** by `shares = int(notional/price)` → `if shares == 0: continue`. At current gross this removes a systematic slice of the book.
