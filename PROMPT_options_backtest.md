# Claude Code — Options backtesting: juice ThetaData, validate scream-buy, update Valquo

**Key is live:** `THETADATA_API_KEY` is set in `.env` and Render. Feed = **ThetaData Standard** — tick
options history to **2016**, NBBO **quotes**, **IV**, **1st-order greeks**, **OI**, all US options;
access **cloud-direct via ThetaData's Python library** (HTTPS/gRPC, no local Theta Terminal).

**Mandate:** build an options backtest with the SAME rigor as the stock model; **(1)** validate the
existing **scream-buy** engine net of the bid/ask spread, **(2)** then test new ThetaData-powered signals
as add-ons through the same gate, **(3)** update Valquo — a sharper alert engine AND a live-tracked options
book. Take the time to do it right. **Expect most add-on signals to reject** — that's what the gate is for;
the wins are the scream-buy validation, the single-leg-vs-spread calibration, and the 1–2 filters that clear.

Keep the discipline: **pre-commit each signal's definition + adoption bar in a results-free git commit
BEFORE running it.** (Separate from this: the git-hygiene + stock-launch items in the prior prompt still
stand if not yet done. This is the options track.)

## Carry over EVERY discipline from the stock backtest
| Stock-model lesson | Options application |
|---|---|
| Point-in-time, survivorship-free | Use the quote/greek/IV **as of the decision timestamp**; **include expired-worthless contracts and delisted underlyings** (a backtest that only sees contracts with an exit price is survivorship-biased). Never peek at the expiry outcome. |
| Pre-commit the gate, results-free (git) | Commit each signal + adoption bar before running it. |
| Held-out, both directions, embargoed boundary | Split the option-trade history by time; require any improvement to replicate in BOTH halves. |
| CPCV + Deflated Sharpe + PBO | Apply where structure allows (cross-sectional signal ranks). For the event-study expectancy use the held-out split + a bootstrap (heavy tails). |
| Coverage guard (silently-empty factors) | Per-contract IV/greek/quote/OI coverage; warn under floor; ship a `signal_coverage` block. |
| Sanity layer (SANE, not just present) | IV in a plausible band; delta sign/range by right; reject crossed/zero/stale quotes; put-call parity spot-check; spread sanity; price > 0. Ship a `sanity_check` block. |
| Costs are decisive; quote BREAKEVEN | Options spreads dwarf stock spreads — **this is make-or-break.** Fill from real NBBO (buy toward ask, sell toward bid); charge commission + spread; report breakeven, not just net. |
| Don't judge a scaling change by per-signal IC | If you z-score option signals, judge on the composite/expectancy, not per-signal rank-IC. |
| Heavy tails → need enough closed trades | Keep `MIN_CLOSED_PER_BUCKET` (~30) before concluding on any bucket; one triple-up moves every statistic. |
| Silent-corruption bug class | A completed run with a wrong number is the enemy — the coverage + sanity blocks must actually gate. |
| Honest verdicts; update handoff/audit/results | Regenerate `OPTIONS_BACKTEST_RESULTS` and update `HANDOFF_STATUS.md` / `CODE_AUDIT.md`. |

## 1. ThetaData provider + data layer
- Provider reads `THETADATA_API_KEY`, cloud-direct Python library, **no-op status dict if absent** (like
  the optional sklearn import) so tests/runs never break without it. Local cache like `bulk.py`; the
  historical pull is a **chunked, resumable background job** (Standard = 4 concurrent, tick to 2016).
- Pull for the backtest universe: chains (strikes/expiries), **NBBO quotes**, tick **trades**, **IV**,
  **1st-order greeks**, **OI**. **Compute gamma from IV** (Black-Scholes; risk-free rate free from FRED —
  do NOT pay for ThetaData's rate tier).
- Align option data to **PIT underlying prices** (existing Sharadar SEP / price history).
- **Universe:** liquid, optionable US names overlapping the scan universe. Enforce a **liquidity filter**
  (min OI/volume, max spread %) so fills are real — illiquid contracts are excluded, never faked.

## 2. Realistic fill + cost engine — build this FIRST; everything rests on it
- Entry/exit at ACTUAL historical NBBO as of the decision time — buy near the ask, sell near the bid
  (configurable aggression, default mid→touch). **Never mid/theoretical.**
- Charge commission + spread; report **breakeven** alongside net P&L.
- Reject any fill on a contract failing the liquidity filter.

## 3. Reconstruct the scream-buy signal + the expectancy backtest (the core deliverable)
- Reconstruct the historical scream-buy **fingerprint** at each date from the stock model's PIT scores +
  technicals + ThetaData IV/flow at that time — **mirror the live alert logic exactly** (same thresholds;
  same contract pick: the current delta/DTE/horizon selector). Bullish → calls, bearish → puts.
- For each reconstructed alert: pick the contract the live engine would, enter at realistic fill, hold per
  the live exit discipline (also sweep a few horizons and a profit-target + stop variant), exit at
  realistic fill, compute P&L.
- Aggregate the **same metrics as the live scorecard**: hit rate, avg win, avg loss, profit factor,
  expectancy/trade, cumulative P&L (fixed 1-contract / 100-share basis). **Backtest ≡ forward scorecard,
  run over history** — so the two can never disagree.
- Report the verdict honestly, broken down by **IV regime, horizon, delta, DTE, and side** — where does
  the engine make or lose money net of spread?

## 4. Construction comparison — single-leg vs vertical spread (decide with OUR data)
- Run the identical reconstructed signal two ways: **(a) single-leg long** (primary/product) and **(b) the
  matched vertical debit spread** (same long strike, sell further OTM). Compare expectancy + risk-adjusted
  (Sharpe/expectancy, hit rate, tail, max drawdown), overall and **by IV-rank regime**.
- Why: single-leg's weakness is that scream-buys often fire when IV is elevated, so you overpay for vol and
  eat theta / IV-crush. The spread arm tests whether capping vega/theta wins on a risk-adjusted basis —
  especially in high IV. Let the **held-out gate** decide which construction ships, possibly
  **regime-conditional** (e.g., single-leg when IV rank is low, spread when high).
- **Premium selling (CSP / covered calls) is DEFERRED to a separate track** — a different (short-vol /
  income) strategy, not the scream-buy engine. Flag it in the handoff with the rationale: harvest the
  variance risk premium by selling CSPs on Valquo book names when their IV is rich.

## 5. Juice ThetaData — new signals as add-ons / filters, each through the gate
Pre-commit each; keep only what clears the held-out bar as a **filter/enhancer on the scream-buy
expectancy** (not standalone noise):
- **IV rank / percentile** (trailing, per name) — gate entries or switch construction when vol is rich.
- **Variance risk premium** — IV vs trailing realized vol.
- **Term structure** — front vs back IV (backwardation = stress).
- **Skew** — put vs call IV.
- **Flow from tick trades** — sweeps/blocks, net premium, **aggressor side** (trade vs prevailing quote),
  volume-vs-OI (DIY unusual activity — the thing we're NOT paying Unusual Whales for).
- **GEX / dealer gamma** — OI + gamma-by-strike (gamma from IV); pinning / vol-regime read.
- **Unusual OI change** day-over-day.

## 6. Update Valquo (the outcome: BOTH)
- **Sharper engine:** set the live scream-buy thresholds / which signals fire / IV filter / preferred
  construction from what cleared the gate. Wire into the live scan + the existing `/api/options-scorecard`.
- **Tracked options book:** emit a dated, live-tracked options "book" (current highest-expectancy setups)
  analogous to the Valquo stock Index, benchmarked forward. Cowork fills real outcomes via the outcome API.
- Keep the expectancy scorecard as the forward source of truth: **backtest calibrates, forward validates.**

## 7. Close-out
- Coverage guard + sanity layer + costs/breakeven ship in the results block on every run.
- Full test suite green + new options tests (provider, fill engine, signal reconstruction, the gate).
- Regenerate `OPTIONS_BACKTEST_RESULTS.(json/md)` and update `HANDOFF_STATUS.md` / `CODE_AUDIT.md` with
  concrete numbers + adopt/reject verdicts.
- Flag anything needing Don. Do NOT re-open the rejected stock-model items.
