# O8 — Index variance risk premium: the backtest that had never been run

`options_backtest/backtest_engine.py` has existed, tested, since the second pass. No result
from it appeared anywhere in the corpus. This is that result.

Threshold pre-registered in `HANDOFF_optionsbot.md` and committed (`f5096c3`) **before** any
run. Verdict rests on **SPY** over **2018-01-01 to 2025-12-31**; pre-2018 is reported
separately and was not permitted to move the verdict.

---

## Two reasons it had never been run — both in the code, neither about data

1. **Stooq, the only data source the script had, is gone.** A bare request returns HTTP 404;
   with a browser User-Agent it returns HTTP 200 carrying a JavaScript browser-verification
   challenge instead of CSV. `csv.DictReader` parses that HTML into an empty dict, so the
   script's own error path reported "could not fetch required data" — a dead feed presenting
   as missing data. Fixed with a source chain: Stooq → **Cboe** (the authoritative publisher
   of VIX/VXN/RVX, and the only free source of ^RVX at all) → **yfinance** (ETFs, ^IRX). The
   source actually used is now recorded in the results JSON.
2. **The script crashed on save, after printing the report.** `json.dumps` cannot encode the
   `date` objects on every `Trade`, so a fully successful run raised `TypeError` and left
   nothing on disk. Fixed with `default=str`.

Neither is a data-availability problem. The engine itself is sound and needed no change.

---

## Primary window — 2018-01-01 to 2025-12-31, default config

20-delta short put, $5 wide, 35 DTE, 50%/2x/21-DTE exits, vol-scaled 2% sizing, weekly
expiries, $100k start. Slippage $0.02/share/leg, commission $0.65/contract/leg.

| | SPY (^VIX) | QQQ (^VXN) | IWM (^RVX) |
|---|---|---|---|
| Total return | **+31.54%** | +3.25% | **−38.40%** |
| Annualized | +4.68% | +1.68% | −5.13% |
| Risk-free used | 2.54% | 2.54% | 2.55% |
| Annualized vol | 15.7% | 16.0% | 13.8% |
| **Sharpe (excess)** | **0.14** | **−0.05** | **−0.56** |
| Max drawdown | −23.2% | −33.3% | −46.8% |
| Trades | 1,905 | 1,907 | 1,892 |
| Win rate | 76.0% | 75.9% | 70.2% |
| Avg win / avg loss | $200 / −$534 | $179 / −$530 | $115 / −$326 |
| Worst trade | −$1,276 | −$1,267 | −$965 |
| COVID (2020-02-15→04-30) | −8.05% | −5.62% | −8.56% |
| 2022 bear | −19.89% | −30.32% | −11.40% |
| Ruin halt | none | none | none |

The classic short-vol shape is intact — win ~76%, avg loss ~2.7x avg win — and the pennies do
not outrun the bricks on two of three legs.

## Pre-2018 — reported separately, and it runs the WRONG WAY

| | SPY 1993-02→2017-12 | QQQ 2009-09→2017-12 | IWM 2009-09→2017-12 |
|---|---|---|---|
| Total return | −53.77% | −31.76% | −11.26% |
| Sharpe (excess) | −0.54 | −0.57 | −0.10 |
| Max drawdown | −62.1% | −37.7% | −22.6% |
| Trades | 5,695 | 2,027 | 1,984 |

The audit's caveat (Dew-Becker et al., Chicago Fed 2025-17: the index VRP **declined** in the
2020s) predicts the old window should look *better*. **It looks worse, on all three legs.**
That is not evidence the VRP rose — it is the cost model biting hardest in the low-VIX
2013–2017 regime, where the modelled credit is smallest and the per-contract cost is fixed.
Which is the finding below.

---

## The mechanism: this is a cost result, not a premium result

Costs are fixed per contract ($2.60 commission + $8.00 slippage = **$10.60 round trip**) while
the credit scales with implied vol. Decomposing every trade log:

| Run | Contracts | Gross P&L (pre-cost) | Commission | Slippage | **Cost / gross** |
|---|---|---|---|---|---|
| SPY 2018–2025 | 8,933 | $139,279 | $23,226 | $71,464 | **0.68** |
| QQQ 2018–2025 | 7,995 | $99,715 | $20,787 | $63,960 | **0.85** |
| IWM 2018–2025 | 5,675 | $29,917 | $14,755 | $45,400 | **2.01** |
| SPY 1993–2017 | 11,334 | $81,343 | $29,468 | $90,672 | **1.48** |
| QQQ 2009–2017 | 5,803 | $38,129 | $15,088 | $46,424 | **1.61** |
| IWM 2009–2017 | 7,333 | $76,382 | $19,066 | $58,664 | **1.02** |

**A gross variance risk premium is present in every single window** — gross P&L is positive
in all six. Execution eats 68% to 201% of it. Slippage is ~3x commission throughout.

This is the *same* mechanism that killed the single-name arm (`$28 of a ~$65 mid credit
consumed crossing two spreads twice`). Moving to index options attacks it — SPY's 0.68 is far
better than single-name's ~0.43-of-credit — **but not by enough.**

### The ceiling, measured (post-hoc, not pre-registered)

SPY 2018–2025 with slippage forced down:

| Slippage/share/leg | Total return | **Sharpe (excess)** |
|---|---|---|
| $0.02 (default) | +31.54% | 0.14 |
| $0.01 (tight, realistic for SPY) | +81.65% | 0.39 |
| $0.005 | +107.10% | 0.49 |
| **$0.00 (free execution)** | **+144.76%** | **0.62** |

At **zero transaction cost** — a fill quality that does not exist — the strategy reaches
excess Sharpe **0.62** against a 21% drawdown. The pre-registered ADOPT bar of 0.50 is cleared
only in that unreachable limit. At realistic index fills it is 0.39, and at the engine's
conservative default 0.14.

---

## Verdicts

* **SPY — INCONCLUSIVE by the pre-registered rule.** Total return +31.54% (>0), excess Sharpe
  0.14 (≥0), no ruin halt, so it does not meet the REJECT condition; Sharpe 0.14 is far below
  the ADOPT bar of 0.50, so it does not adopt. Reported as pre-registered, not rounded either
  way.
* **QQQ — REJECTED** (excess Sharpe −0.05, negative).
* **IWM — REJECTED** (excess Sharpe −0.56, −38.40% over 8 years, −46.8% drawdown).
* **Pre-2018 — REJECTED on all three**, and explicitly not used to set the verdict.

**Recommendation: do NOT proceed to O8 stage 2 (porting the arm to real index chains).** The
zero-cost run bounds the whole approach: the ADOPT bar is unreachable at any achievable
execution quality, so better data on the chain would refine a number that is already known to
top out below the threshold. The honest positive finding is narrower and worth keeping — **the
index VRP is real and gross-positive in every window tested; it is simply smaller than the
cost of harvesting it with a 4-leg, 35-DTE, stop-managed structure.**

If short vol is ever revisited, the evidence points at *structure*, not underlying: fewer legs,
fewer round trips, longer holds. That is a different test, and this one does not license it.

## Caveats that cut FOR the strategy — carry them

* **No skew.** One IV for every strike understates the credit at the 20-delta put, so real
  collected credit is larger than modelled. These numbers are a **floor**, not a level.
* **No term structure.** VIX is a 30-day number applied at 50 and 22 DTE alike.
* **The stop model is pessimistic on slow losers** (next-close fill, no intraday touch).
* **No portfolio dimension.** A ladder of 10 overlapping SPY spreads is one trade wearing ten
  hats; nothing here models that, and it makes the drawdowns understated if anything.

Because the floor caveat is real, the *gross*-premium finding above is the robust part of this
result and the *level* is the soft part. Both point the same way here, which is why the
recommendation is a recommendation and not a proof.

Raw stats, provenance and cost decomposition for all six runs:
`options_backtest/index_vrp_summary.json`. Full equity curves and trade logs are regenerable
(`python run_options_backtest.py --etf SPY --start 2018-01-01 --end 2025-12-31`) and are not
committed — 4.9 MB of derived data.
