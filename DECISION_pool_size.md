# How big should the pool be? — `POOL-SIZE`

**For Don. Prepared under `PREREG_pool_size.md`, whose decision rule was fixed before any number
was read. Nothing here is adopted.**

## The short answer

**Wider kept helping all the way to the full pool, on both periods. The rule you set picks the
FULL POOL.** The one place more names hurt is a **drawdown step at 1,000 names**, and the extra
return is **a size bet rather than selection skill**.

---

## 2009-2026 — the ladder

One construction throughout (top decile by the shipped composite, score-weighted, 8% cap, 0.30
band, quarterly, net of the size-aware cost model); only the pool changes.

| pool | net Roth | vs SPY | max drawdown | turnover | cost | weight under $300M | SMB |
|---|---|---|---|---|---|---|---|
| incumbent $10B tier | 17.16% | +1.93pp | −23.03% | 2.44 | 9.6bps | 0.0% | +0.08 |
| 500 largest | 17.19% | +1.96pp | **−20.24%** | 2.43 | 10.8bps | 0.0% | +0.05 |
| 1,000 largest | 19.02% | +3.79pp | −25.74% | 2.22 | 17.3bps | 0.0% | +0.15 |
| 1,500 largest | 22.95% | +7.71pp | −27.60% | 1.93 | 29.3bps | 3.6% | **+0.64** |
| 2,000 largest † | 24.95% | +9.72pp | −27.81% | 1.86 | 35.6bps | 8.6% | **+0.79** |
| **full panel** | **24.95%** | **+9.72pp** | −27.81% | 1.86 | 35.6bps | 8.6% | **+0.79** |

**† The 2,000 rung is the full panel.** The panel carries a median of **1,557 names per date**, so
a 2,000-name trim never binds — every figure is bit-identical. It is kept in the table for
completeness and that step is **vacuous by construction**. So the ladder really tops out between
1,500 and full.

### Your rule, step by step

> the largest pool whose net return is not lower than the next-smaller pool's and whose max
> drawdown is not more than 3pp worse

| step | Δ return | Δ drawdown | verdict |
|---|---|---|---|
| 500 vs incumbent | +0.03pp | **+2.79pp better** | CLEARS |
| **1,000 vs 500** | +1.83pp | **−5.50pp worse** | **FAILS** |
| 1,500 vs 1,000 | +3.92pp | −1.86pp | CLEARS |
| 2,000 vs 1,500 | +2.00pp | −0.21pp | CLEARS |
| full vs 2,000 | 0.00pp | 0.00pp | CLEARS (vacuous) |

**The 1,000-name step is the only failing step anywhere in this item** — on either period.

**THE TWO READINGS OF YOUR RULE DISAGREE, and the register fixed which one wins before the
numbers existed.** Read literally — *the largest pool whose own step clears* — the answer is the
**full panel**. Read cumulatively — *every step up to it must clear* — the answer is **top 500**,
because the ladder is blocked at 1,000. **The literal reading is the registered primary and is
the answer; the cumulative one is reported as the sensitivity it was pre-committed to be.**

---

## 1999-2008 — out of sample, and it agrees

**A LABELLED PROXY FOR POOL WIDTH, NOT A TEST OF THE SHIPPED COMPOSITE.** `institutional` has no
pre-2009 source at all and `insider` reaches only 0.307 by 2008, so this scores **five themes**
(value, quality, momentum, capital_discipline, size). Built from the freeze's **full raw**
SEP/SF1/SFP — 11,052 names, 39 quarterly dates, 1998-12-31 → 2008-07-10 — with the shipped panel
builder, **not** from `data/backtest`. Read once.

| pool | net Roth | vs SPY | max drawdown | turnover | cost |
|---|---|---|---|---|---|
| 500 largest | 9.77% | +10.59pp | −40.83% | 2.01 | 17.0bps |
| 1,000 largest | 11.12% | +11.94pp | −39.25% | 1.94 | 24.7bps |
| 1,500 largest | 12.01% | +12.83pp | −39.93% | 1.92 | 33.3bps |
| 2,000 largest | 14.10% | +14.93pp | −39.09% | 1.87 | 41.0bps |
| **full** | **18.50%** | **+19.32pp** | **−36.10%** | **1.52** | 102.9bps |

**EVERY step clears, and both readings agree on the full pool.** The full pool also has the
**best drawdown** and the **lowest turnover** of the five — while paying **102.9bps of realised
cost against 17.0bps at 500**, so width wins *net of a cost model charging six times more for
it*.

**Three things must travel with this table.** Its **levels are not comparable** to 2009-2026
(five themes, 39 dates, drawdowns near −40%, and a decade in which SPY was roughly flat — so
every vs-SPY figure is inflated by the era, not by skill). Its universe carries **50.68%
in-window delisting** against the derived path's 10.68%, a 4.7× difference that is exactly why
the register forbade `data/backtest` — and `PANEL-EXT-CENSUS`'s pre-committed `K3` would have
**failed** that profile as carrying too many later-delisters, so **the shape is the claim and the
levels are not**. And it spends the **late portion** of the charter's 1990-2008 era, leaving
1990-1998 a stub of an era meant to be read whole.

---

## What the extra return actually is

**A size bet. SMB switches on exactly where the return jumps:** +0.08 at the incumbent and +0.05
at 500, then **+0.15 → +0.64 → +0.79** across 1,000 → 1,500 → 2,000. `R1`'s own alignment control
reproduces exactly (SPY-on-MKT beta 0.9327, R² 0.9878), so the loadings are real and not a
windowing artefact. **No alpha claim is made** — the register inherited that prohibition from
`INDEX-CHOICE`.

## Where the data gets worse, measured rather than assumed

You asked for the small end to be measured. It degrades monotonically:

| market cap | worst-theme missing rate | names |
|---|---|---|
| under $300M | **0.4728** | 553 |
| $300M – $1B | 0.4384 | 1,166 |
| $1B – $10B | 0.2985 | 2,216 |
| over $10B | **0.1956** | 1,335 |

**2.4× worse at the small end.** And the full panel puts a **mean 8.6%** and a **maximum 28.2%**
of its weight exactly there — which **refutes my own registered expectation** of under 5%. Every
rung up to 1,000 holds **0.0%** under $300M, so the entire micro-cap exposure arrives between
1,000 and 1,500 — **the same step as the SMB switch and the drawdown break.**

## The penny/nano floor could not be tested here

Removing it changed the universe by **two names** (3,037 → 3,039), for +0.32pp of return. So it
measures two names, not a floor. The reason is that the export's universe is **already cap-ranked
upstream**, leaving the floor almost nothing to drop. Testing it properly needs a universe that
contains nano-caps — the raw-table route part (b) built.

---

## What this means for the decision, and what it does not

* **On your rule, the pool should be the full panel** — and on 2009-2026 that is the same book as
  the 2,000 rung and only one step above the 1,500 rung (`INDEX-CHOICE`'s arm 2).
* **The honest caveat is that this is a size exposure**, and `R1`'s re-run found SMB *not*
  significant for the long-short spread on the corrected panel. So the wider pool is leaning on a
  factor premium this project has not itself demonstrated.
* **If the 1,000-name drawdown break is the thing you care about**, the cumulative reading of
  your own rule says top 500 — which gives up 7.8pp of return for 2.8pp less drawdown.
* **Nothing is adopted.** Changing the pool is a **vintage event** and it is your call; this item
  routes it rather than taking it.

`PREREG_pool_size.md`; `data/free_analysis/POOL_SIZE_LADDER.json`, `POOL_SIZE_DIAG.json`,
`POOL_SIZE_FACTORS.json`, `POOL_SIZE_ARM7.json`, `POOL_SIZE_OOS_CENSUS.json`,
`POOL_SIZE_OOS.json` (gitignored).
