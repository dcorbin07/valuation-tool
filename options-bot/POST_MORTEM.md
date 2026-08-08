# Post-mortem — 38 trading days of live SIM data

**Window:** 2026-06-08 to 2026-07-31. Four bots deployed, three produced data,
one never ran at all. Data pulled before the Oracle instance was terminated.

The performance numbers here are worthless. What the data shows instead is a
textbook failure — one where every safety mechanism reported healthy, right up
to the point where the book was 2.85x levered long and nothing was watching.

---

## The one-line version

**Mean-reversion ended the period holding 206 long positions at 285% gross
exposure, on margin, in a strategy designed to be dollar-neutral at 10%
volatility — and the weekly report described it as 5.5% volatility, Sharpe
0.01, "effectively independent (ideal for diversification)."**

---

## 1. What actually happened to the book

Position count, every fourth trading day:

    trend       25  25  25  25  25  25  25  25  25  25
    momentum    27  33  37  39  42  44  43  43  44  45
    reversion   20  52  81 102 130 153 167 179 195 205

Gross exposure as a share of equity:

    trend       36% -> 36%    (stable, never drifts)
    momentum    11% -> 21%    (slow creep)
    reversion   30% -> 285%   (monotonic ratchet)

Reversion's cash went from +$140,274 to **-$368,463** on a $199k account. A
long-only book funded by negative cash is leverage, and nothing in the system
objected.

**The ordering is not random — it tracks signal turnover exactly.** Trend holds
a fixed 25-ETF basket, so its price map always covered every held name and its
exits always filled: perfectly flat, immune. Momentum ranks on 12-1 return,
which is stable month to month, so only a few names rotated out per rebalance:
slow creep. Reversion is a 21-day z-score — the fastest-turning signal in the
system — so it shed and added names constantly, and every single name it tried
to exit stayed in the book. The bug's severity was proportional to how often
each strategy changed its mind.

## 2. Why nothing caught it

Three failures compounded, and the third is the one worth remembering.

**The exit bug.** Each orchestrator built its price map from the current
selection only. A name that dropped out of the top/bottom-N had no price, and
`apply_orders_to_sim` silently skipped any order it couldn't price — at DEBUG
level. Exits were generated correctly by the portfolio layer and then thrown
away.

**The regime-gate bug.** With SPY above its 200-day MA for the whole window,
shorts were suppressed every cycle. The strategy layer then gross-normalized
over the surviving longs, so removing the short book didn't shrink the
position, it doubled the long one. That is why the final book is 206 long / 0
short rather than a balanced pair.

**The risk caps only ever constrained the TARGET, never the BOOK.** Each day
the risk manager correctly sized that day's target portfolio to its limits. But
the actual holdings were the accumulated union of every target ever set, and
nothing reconciled the two. The caps were computed on a number that had stopped
describing reality weeks earlier.

## 3. The part that should be uncomfortable

`SimPortfolio.total_equity` marks a holding with no price at its average cost.
So every stranded position contributed **exactly zero** P&L, forever.

Measured on the final day:

    trend       25 positions, |unrealized| $2,286  =>  $91.43 per position
    momentum    46 positions, |unrealized| $1,317  =>  $28.63 per position
    reversion  206 positions, |unrealized|    $49  =>   $0.24 per position

A 206-name equity book that moves $49 in a day is not a market outcome. It is
an accounting artifact.

**And that artifact is what disabled the kill switch.** The kill switch reads
daily P&L. Daily P&L was near zero because the book was frozen. The final state
files show it plainly — `starting_equity` and `last_seen_equity` identical for
all three bots:

    reversion: starting 199235.499, last_seen 199235.499

**The bug that created the danger was the same bug that hid it.** The safety
mechanism was not merely bypassed; it was fed a number manufactured by the
failure it existed to catch.

## 4. What the reporting layer said

From `data/reports/correlation_2026-08-02.md`, generated the day this was shut
down:

> **reversion** — Total return: -0.01%. Annualized volatility: 5.5%.
> Sharpe ratio: 0.01.
>
> **momentum vs reversion:** +0.01 — very weak — effectively independent
> (ideal for diversification)

Against a 206-name, 2.85x-levered, long-only equity book, the real volatility
was somewhere near **51%** — roughly nine times what was reported. A 10% market
drop would have taken about **29% of the account**.

Nothing in that report looks wrong. The numbers are plausible, internally
consistent, and precisely formatted. It even correctly cautions that
correlations under 20 overlapping days are noise — sophisticated-sounding
prudence about entirely the wrong risk. Had this been running with real money,
the report would have kept saying "low volatility, well diversified" until the
first bad week took a third of the account.

**The lesson is not "test your code." It is that a monitoring system built on
the same broken assumptions as the thing it monitors will confirm that
everything is fine.** Trend and momentum were reported with the same apparatus
and were largely fine — which made reversion's numbers look like just another
row in the table.

## 5. The bot that never ran

The options bot produced **no equity curve, no journal, no sim directory —
nothing at all** in 38 days. Its manage job writes a snapshot even when holding
zero spreads, so a missing file means the job never once completed. It was
enabled, "active" in systemd, and silent. Nobody noticed for two months,
because absence of output looked identical to a quiet strategy.

## 6. What is actually salvageable

**Trend's equity curve is clean and usable.** 38 days, 25 positions throughout,
17-36% gross, -0.14% total return, 2.8% annualized vol. Exits filled correctly
because its fixed basket always covered its holdings. It is a real, unbroken
record of a vol-targeted cross-asset trend book — and its 17-36% gross confirms
the separate finding that the old vol-targeting math under-deployed by roughly
3x against a stated 10% target.

**Everything else is evidence, not performance.** Momentum and reversion curves
cannot be repaired: a position frozen at cost cannot be re-marked after the
fact. The options bot has nothing to salvage.

**Nothing here says anything about whether these strategies make money.** 38
observations cannot separate skill from noise even with clean data, and three
of four books were structurally broken. Any number in this dataset that looks
encouraging is an artifact.

## 7. Fixes already made

All of the above is fixed in the code, with regression tests that fail against
the old version and pass against the new — verified by running them against a
pre-change copy, not asserted:

- Exits now price from the whole scored universe, with a quote backfill for
  names that left it entirely, and unfilled orders are surfaced loudly instead
  of skipped at DEBUG.
- The regime gate now holds suppressed capital back rather than doubling the
  longs (measured: gross 1.00 -> 0.50, net +1.00 -> +0.50).
- Vol targeting is correlation-aware with shrinkage and a hard leverage cap.
- The backtest runs the kill switch and regime gate, so it tests what trades.

Test counts: **148** (quant_bots) / **181** (options) / **36** (screener),
from zero in the screener.

---

## The honest summary

Two months of compute produced no usable performance data and one genuinely
valuable finding: a system can be fully deployed, systemd-managed,
crash-restarting, emitting well-formatted weekly reports with correct
statistical caveats — and be completely detached from reality, with every
indicator green.

That is worth more than a Sharpe ratio. It is also the more interesting thing
to be able to talk about.
