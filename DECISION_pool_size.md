# How big should the pool be? — `POOL-SIZE`

**For Don. Prepared under `PREREG_pool_size.md`, whose decision rule was fixed before any number
was read. Nothing here is adopted.**

---

> ## CORRECTION TO THE CORRECTION, 2026-10-06 (`UNIVERSE-BIAS` part 2)
>
> **The correction below was computed on a panel that was quietly missing a theme, and two of its
> statements are wrong. The headline conclusion is not.**
>
> **My defect.** The full-universe export I built wrote `fundamentals.csv`, prices and the
> benchmark — and not `insiders.csv`. Without that file the `insider` theme goes **constant**, so
> the column is present, 100% populated, and contributes nothing. The corrected book was therefore
> a **six-theme** book being compared against a **seven-theme** one, and the runner reported
> "themes 7" on both sides because it counted columns *present*. A universe comparison in which a
> theme also moved is not a universe comparison. Fixed, re-run with all seven themes alive on both
> sides, and a guard now **refuses** to compare two panels whose live theme sets differ.
>
> **What does not change: the wider pool still loses on the corrected universe.** The advantage
> goes **+7.24pp → −3.26pp** (it was −4.14pp on the six-theme panel). Still a sign reversal, same
> size, same reason. And the census is untouched: the widest book still holds **63.3%** of its
> weight under $300M against 10.9% on `data/backtest`, and 80.6% of the small-and-later-dead 2009
> names are still missing.
>
> **What does change, and you should know both.**
>
> **(1) The incumbent moves DOWN, not up.** I told you the $10B tier "survives and improves
> slightly" at +0.52pp. On the seven-theme panel it is **18.42% → 18.02%, i.e. −0.40pp**. It still
> survives — that is a small move, and still above the published 17.16% — but the direction I gave
> you was wrong and it came from the missing theme.
>
> **(2) Your rule no longer picks the incumbent outright on the corrected universe.** The literal
> reading now picks **top 1,000** (18.17%, drawdown −28.29%) and the cumulative reading still picks
> the incumbent, so the two **disagree** where before they agreed. The gap is 0.15pp of return on a
> slightly better drawdown — well inside what adjacent rungs can be told apart by, which the
> register said in advance. **It does not change my recommendation**: the ladder on the corrected
> universe is essentially flat from the incumbent to 1,500 (18.02 / 17.83 / 18.17 / 17.76) and only
> the full pool is clearly worse, so there is no wider pool worth moving to.
>
> **Recommendation unchanged: keep the $10B tier for 2026-10-22.**
>
> There is also a larger finding that is not about the pool at all, and it has its own memo —
> **`DECISION_canonical_universe.md`**. Short version: on the corrected universe the *research*
> headline (+7.17%/yr top-decile alpha vs the equal-weighted universe) falls to **+2.83%/yr at
> t 1.08** and stops being separable from zero, and nine of eleven testable public claims no longer
> hold. Your Index is the part that survives.

---
---

> # CORRECTION, 2026-10-06 (`UNIVERSE-BIAS`) — READ THIS BEFORE THE REST OF THE MEMO
>
> **The answer below is overturned. The wider-pool advantage was an artefact of which names
> `data/backtest` contains, and on a corrected universe it REVERSES SIGN. Your rule, applied
> unchanged, now picks the INCUMBENT $10B TIER on both of its pre-committed readings.**
>
> **Your Index backtest is fine.** The $10B incumbent reads **18.94%** on the corrected universe
> against **18.42%** on `data/backtest` at the same vintage — it goes slightly *up*. The published
> 17.16% is a third object (the banked panel at 2026-07-24) and that gap is the data vintage, not
> the universe. Nothing about the shipped Index needs restating.
>
> **What went wrong.** `data/backtest` is built by ranking today's tickers by **today's** market
> cap and keeping the top 3,000. A company that was a micro-cap in 2009 and delisted in 2013 has
> no 2026 market cap at all, so that ranking cannot see it. Measured: of 3,327 names that were
> under $300M in 2009 **and later died, 80.61% are missing** from `data/backtest`, against
> **42.10%** of the small names that survived. The omission is 1.9× worse for the dead ones — which
> is exactly the direction that flatters a wide pool, because a wide-pool book is never charged for
> having held the losers.
>
> **The ladder, rebuilt from the raw data through the same builder, same dates, same seven themes
> — only the universe changes:**
>
> | pool | `data/backtest` | corrected | change |
> |---|---|---|---|
> | **incumbent $10B** | 18.42% | **18.94%** | **+0.52pp** |
> | 500 | 18.18% | 18.77% | +0.60pp |
> | 1,000 | 19.54% | 17.93% | −1.61pp |
> | 1,500 | 19.55% | 16.62% | −2.93pp |
> | **full pool** | 25.65% | **14.80%** | **−10.85pp** |
>
> The wider-pool gain goes from **+7.24pp to −4.14pp**. On the corrected universe the widest pool
> **loses to SPY by 1.02pp**, its drawdown is −37.54% against the incumbent's −27.94%, and its
> second half earns 11.17% against 27.06% before.
>
> **Why, in one number.** On `data/backtest` the full-pool book holds a mean **10.9%** of its
> weight in names under $300M. On the corrected universe it holds **61.9%**, peaking at 79.6%. The
> widest pool was never really a wide mid-cap book; it was a micro-cap book wearing one.
>
> **It is not a data-quality problem, and that cuts against the obvious story.** The extra names
> are *better* documented at the small end, not worse (worst-theme missing rate 0.3482 corrected
> against 0.4453 restricted). And trading costs explain only about a ninth of the reversal
> (1.18pp of 10.85pp). The remaining 89% is simply the names.
>
> **One thing below survives intact and one does not.** The *size bet* is real: SMB loadings are
> essentially unchanged by the correction (+0.185 → +0.749 before, +0.176 → +0.769 after). What
> collapses is the part the size factor cannot explain — **+8.30%/yr down to +1.67%/yr** on the
> full rung. That is precisely the quantity `POOL-SIZE` declined to call alpha. It was right to
> decline, and the number it declined to claim is the one that was not real.
>
> **Recommendation: keep the $10B tier for 2026-10-22.** It is the only pool whose case does not
> depend on the universe defect, it is the one your own rule now selects on both readings, it has
> the best drawdown of the five, and it is already what the Index runs. If you later want a wider
> pool, the thing to ask for is not a bigger number — it is a universe that contains the companies
> that failed.
>
> *Everything below is left exactly as written on 2026-10-05, because the reasoning that produced
> a wrong answer is worth keeping next to the correction. Read its figures as describing
> `data/backtest`'s universe, not the market.* Full record: `HANDOFF_edge_audit.md`
> `UNIVERSE-BIAS`.

---

## The short answer

**SUPERSEDED 2026-10-06 — see the correction above.**

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
