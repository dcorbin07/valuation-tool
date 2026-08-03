# Second pass — status

**Test counts: 106 → 124 (quant_bots), 181 (options). Both green, verified from a clean zip extract.**

This pass ran into a hard stop partway through: the parallel agents doing the work hit the account's monthly spend limit and were terminated mid-edit. I recovered the tree, repaired what was left half-applied, and finished the highest-value items by hand. Below is an honest account of what landed and what didn't — the "not done" list is real work, not a formality.

---

## Landed and verified

### Correlation-aware vol targeting (the big one)

`trend/risk.py` grew from 200 to ~690 lines. The old estimator used a weighted average of **single-name** vols, which ignores diversification entirely — a 60-name book at 35% single-name vol got scaled to 27% gross and realized 3-6% vol against a stated 10% target.

It now estimates portfolio vol as `sqrt(w' Σ w)` from the actual return panel, with **Ledoit-Wolf-style shrinkage toward a constant-correlation target**. That matters more than it sounds: a 60-name correlation matrix has ~1,770 free parameters estimated from 63 observations. Raw sample correlations there are noise, and noise in this particular direction produces *overconfident diversification* and too much leverage. The shrinkage intensity scales with the data-to-parameter ratio and is floored at 0.20 — we never fully trust a 63-observation correlation matrix, because equity correlations jump precisely when you need them not to.

Guards: `max_vol_scale = 2.0` caps how far vol targeting may lever up, and it logs when it binds. Names with no usable return history are excluded from Σ rather than crashing the estimate. If the panel is missing or too short, it falls back to the old method and **says so in the log** rather than switching silently.

The return panel is plumbed through the signal layer (`recent_returns` on the score and selection objects), so no extra API calls — the closes were already being fetched and thrown away.

Expect gross exposure to roughly double or triple. That's the point: the SIM data will finally describe the book you'd actually deploy.

### The regime gate no longer makes the bots 100% net long

Suppressing shorts used to gross-normalize over the surviving longs, so removing the short book *doubled the long one*. Net went from ~0.00 to **+1.00**. Two strategies documented as dollar-neutral were running single-sided equity beta on most days of most years, and nothing said so.

Now the denominator includes the suppressed shorts, so their capital stays undeployed. Measured, both bots:

```
normal L/S    gross=1.00  net=+0.00
regime-gated  gross=0.50  net=+0.50     (was gross=1.00 net=+1.00)
```

`tests/test_regime_exposure.py` — 18 tests across both bots, including one that reads the orchestrator source to assert it actually hands the suppressed shorts over. The strategy fix is inert without that, and it *was* inert when I found it half-applied.

### Screener value score is no longer a constant

`dcf_upside` — 35% of the Established composite — returned a constant 50 for every name, every day, because nothing computed it. Replaced with sector-relative percentiles of **earnings yield** and **EBIT/EV**, per your call.

All three value metrics are expressed as *yields* rather than multiples, so losses and negative enterprise values rank at the bottom instead of the top — a P/E of −3 is not cheap, but a naive multiple sort puts it first. Names with non-positive EV are dropped from the EV-based metrics and the weight renormalizes onto what's left.

Verified on a synthetic cross-section: value now spans 9.1 to 90.9 where it was previously 50.0 for everyone.

I also found and fixed the wiring gap the agent didn't reach: `pipeline.py` still called its own local `compute_ev_sales_percentiles`, which only ever set the *Speculative* bucket's input. The new score would have been `None` → neutral → the same constant, by a different route. It now calls `scoring.compute_value_percentiles`, a strict superset, and the dead local function is gone.

### Options backtest now matches the deployed bot

Vol-scaled sizing ported verbatim from `risk.py` (linear ramp, 1.0 at IV 0.40 down to 0.40 at IV 1.00), `max_contracts_per_spread`, the deployed-capital cap, real third-Friday expirations instead of `today + 35 days`, `bisect` on the rate lookup, and an explicit **ruin check** so equity can't compound through zero.

Sharpe now subtracts the risk-free rate and reports both figures — `sharpe` and `sharpe_raw`. At ~4% rates against this strategy's ~5% vol the old number was inflated by roughly 0.8, which on a low-vol strategy is most of the headline.

**The no-edge property still holds**, which is the check that matters most. Fed synthetic GBM with IV pinned to realized vol — zero variance risk premium by construction — the engine returns −45.6%, Sharpe −1.59, over 934 trades at a 64.8% win rate. It does not manufacture edge, and the cost model bites.

### Options bot correctness

`portfolio.py` was substantially rewritten (+397/−120) covering the `and`-vs-`or` quote guard, the P&L-written-before-the-guard inflation, deployed-dollars unit consistency, and the fingerprint duplication (now one shared `fingerprints_from_positions` reading width from config, instead of two verbatim copies hardcoding `(5.0, 10.0)` and emitting seven fingerprints per real spread).

I repaired one crash the agent left behind — it referenced a `_sim_initial_cash_cache` attribute it never added to `__init__`, which broke `open_job` in SIM entirely.

### Deploy pipeline

`deploy/deploy.sh` replaces the eleven-step zip-and-scp flow with one command. It refuses to run on a dirty tree, fast-forwards only (never merges — a merge conflict on a production box mid-session is a bad place to be), installs dependencies **and runs both suites before touching a single service**, so a bad commit stops the deploy while the old bots keep running. Verified: the dirty-tree guard fires correctly.

`deploy/backup_state.sh` mirrors `data/` to a second private repo nightly. See `DEPLOYMENT.md` for why this matters more than which host you're on.

---

## Not done — carried forward

These were in scope and did not land. Roughly ordered by value.

**Screener — most of the list.** Only `config.py` and `scoring.py` were reached before the cutoff. Still outstanding:
- `pit_data._pit_point` mixing quarterly and annual figures (`opm` drops 4x the instant a 10-Q lands; corrupts 3 of 6 factors). Sharadar's `ART` dimension fixes this for free, so it may be worth doing as part of that work rather than twice.
- `run_backtest.py` still scores with its own factor set instead of `scoring.py`, and still uses the ~300 *largest* US companies as its universe — the exact inverse of the target.
- The forward-return tracking loop is still unwired; `run_review` will still hand an all-NULL table to the LLM.
- The health gate still aborts on a single feed error across ~13,000 tickers.
- Insider score still spans [25,75] not [0,100], still saturates at ~$1M, still collapses unnamed filers into one buyer, still counts option exercises toward the buy cluster.
- `edgar._annual_series` still keys by filing fiscal year, so recent IPOs lose their growth history.
- No test suite. This is the big one — it's the only codebase here with zero tests.

**Options bot — the tail.** `screener/screener.py` (ATM-distance cap, `spread_max_loss` using config width instead of actual), `scheduler.py` (equity curve still written 12x/day, which will distort correlations against the other three bots), the naming inversions in `strategy.py`, `calendar.py`'s 2027 holiday cliff, and the README drift.

**Equity bots — the backtest.** `core/backtest.py` improvements (kill switch and regime gate still absent, so it still doesn't test what trades), no reversion backtest, warmup still measured in calendar days when it means trading days, `PriceHistory` still O(n) per lookup with no bulk-load path. That last one matters for the Sharadar work specifically.

**Everywhere — README drift.** Documented at length in `FINDINGS.md` §7 and largely not yet corrected.

**Not attempted:** moving `data/` out of the repo working tree. It needs changes to every service unit plus the path handling, and I'd rather do it deliberately than as a footnote. `git clean -fdx` deletes gitignored files, and it's exactly what you reach for when a pull goes wrong — so this is a real hazard, just not an urgent one.

---

## One correction to FINDINGS.md

I flagged `claude-opus-4-8` and `claude-sonnet-4-6` as "almost certainly 404." **Both are valid and Active**, with retirement dates in 2027. I was wrong; the screener isn't broken there and no change is needed.

The actual near-term hazard is `claude-opus-4-1-20250805`, which is deprecated and retires **2026-08-05**. Not currently in the codebase, but worth knowing if it ever gets added.

Worth flagging separately: Claude 4.7 and later use a newer tokenizer producing roughly **30% more tokens for the same text**. So migrating `claude-sonnet-4-6` → `claude-sonnet-5` is not the price cut the per-token headline suggests.

---

## What I'd do next

1. **Deploy this and reset the curves** (`FIXES.md` has the sequence; `reset_sim_curves.py` archives rather than deletes). The vol-targeting change means the new curves describe a materially different book than the old ones — another reason the old data isn't worth keeping.
2. **Oracle → Pay As You Go** (5 minutes, free, removes the reclamation risk) and **set up the state backup** (20 minutes). See `DEPLOYMENT.md`.
3. **Then Sharadar** — and do the screener's `pit_data` fix as part of it rather than separately, since `ART` solves the quarterly/annual mixing for free.
