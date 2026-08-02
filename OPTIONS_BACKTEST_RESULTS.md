# Options backtest — scream-buy validation (2026-08-02)

Full universe: **55 liquid optionable names, 2016-2025 (10 complete years), 1,540 closed
trades** from 8,214 candidate days and 1,841 reconstructed alerts. Every number below is **net
of spread and commission at the punishing fill** (buy the ask, sell the bid, $0.65/contract/leg).

Reconstruction mirrors the live engine exactly and is not a reimplementation: the alert comes
from `intraday.signals.evaluate` + `notify.screaming_buys`, and the scoring from
`options_tracker._stats` / `._bucket_of` — the same functions the forward scorecard uses, so the
two cannot drift apart.

---

## The headline, and why it is not the whole story

    closed trades      1,540
    hit rate           37.4%
    avg win           +120.4%
    avg loss           -55.3%
    profit factor      1.30
    EXPECTANCY/trade   +10.4%
    cumulative P&L     $143,723   (1 contract per trade)

A 37% hit rate whose winners more than double while losers roughly halve is exactly the payoff
shape the tracker was built to measure. **Hit rate alone would have called this a losing
strategy.**

### It clears the pre-committed held-out bar — but decays hard

    first half   2016-01-19 .. 2020-12-07    n=770   exp=+16.4%   pf=1.51
    second half  2020-12-09 .. 2025-11-03    n=770   exp= +4.4%   pf=1.12
    -> positive in BOTH halves: TRUE

Positive in both, so the bar is met. But the second half retains barely a quarter of the first
half's expectancy. By year it is positive in **7 of 10**, and the misses are recent: 2022
(-11.4%), 2023 (-4.6%), 2025 (-0.1%).

### THE DECISIVE CAVEAT: dollar P&L is almost entirely tail-driven

    all 1,540 trades      exp=+10.4%    cum = $143,723
    drop the best 1%      exp= +9.0%    cum =   $2,767
    drop the best 5%      exp= +2.3%    cum = -$151,760

**Fifteen trades are 98% of the dollar profit.** Drop 5% of trades and a decade of trading is
deeply negative. The single best trade returned +766%.

Note the split, because it changes the recommendation rather than just qualifying it:
**percentage expectancy is fairly robust** (+10.4% -> +9.0% after removing the top 1%) while
**dollar P&L is not** ($143.7k -> $2.8k). The gap exists because the book buys ONE CONTRACT per
signal, so expensive contracts dominate dollars. Sizing by fixed dollar risk rather than fixed
contract count would track the percentage figure, and is the obvious next construction test.

In the recent regime the margin is thin either way: 2021+ gives +4.8% per trade, and +2.7% after
dropping the top 1%.

---

## Where the engine makes and loses money

    BY EXIT REASON            n      exp
      target (+100%)        473   +138.8%
      time_stop (half DTE)  192     +8.9%
      stop (-50%)           860    -59.1%
      expiry                 15    -29.3%   (<30, not actionable)

56% of trades hit the stop. Realised stop loss is **-59.1%, not -50%** — the stop triggers on a
daily mark and the fill is worse than the trigger. A backtest that assumed -50% would overstate
the edge.

    BY IV REGIME (ATM IV at entry; quartiles 18.1% / 33.1%)
      low IV     385   +17.7%
      mid IV     770    +6.3%
      high IV    385   +11.5%

    BY DTE                          BY DELTA
      45-55   548    +7.8%            <0.30     192    +4.4%
      55-65   519    +7.2%            0.30-0.40 1125  +11.6%
      65-75   473   +17.0%            >=0.40     223   +9.6%

The live 35-delta choice is the best of the three delta buckets, so that parameter is already
right. The longest DTE band (65-75) more than doubles the shorter ones, which is a testable
refinement rather than a finding — it has not been through a held-out gate.

    BREADTH: 55 names with >=10 trades, 37 positive (67%).
      best  PFE +69%, TGT +67%, AMD +58%
      worst NKE -30%, VZ -23%, UNH -21%

Two thirds of names positive means the result is not one or two lucky tickers, even though the
DOLLARS are a handful of lucky trades.

---

## Verdict

**The scream-buy engine survives realistic trading costs and clears the pre-committed both-halves
bar, but it is not demonstrated to be reliably profitable.** Three reasons to be careful:

1. Dollar profit rests on ~15 trades out of 1,540.
2. Expectancy decays from +16.4% to +4.4% across the held-out split, and three of the last four
   years are flat or negative.
3. The sample is 2016-2025, a period dominated by a bull market in exactly these large caps —
   a long-call strategy is structurally advantaged in it.

The honest summary is **"positive expectancy, thin and fading, and far too tail-dependent to
size aggressively"** — not "the scream-buy engine works".

---

## Method notes (things that were wrong before they were right)

Four silent bugs were found and fixed while building this; each would have produced a confident
but meaningless verdict:

1. **Split-adjustment mismatch.** Sharadar `closeadj` is retro-adjusted; option strikes are
   as-traded. AAPL 2019-05-07 read 48.34 against real strikes of 150-200 (4:1 split, Aug 2020).
   Plain `close` is ALSO adjusted, so `closeunadj` is the as-traded series. Symptom was silent:
   ATM IV solved to None on every pre-split date and contracts came from the wrong end of the
   ladder. Technicals now use adjusted prices, all option maths uses as-traded.
2. **Risk-free rate refetched per call.** A failed FRED fetch retried on every call (19.7s then
   60.3s each) because the guard was on an empty cache and the path was relative. It presented
   as slow option maths.
3. **Year pulls failed silently.** 11 of 30 died on gRPC errors with no retry and no record;
   AAPL was missing 2021-2023 while the run proceeded as if complete. Now quarterly chunks with
   retry/backoff, and gaps are recorded and the name excluded rather than under-sampled.
4. **Ticker renames.** META returns nothing before June 2022; FB returns 101,544 rows for
   2019Q1 alone. Historical aliases are now mapped.

Cost realism: fills cross the spread in the punishing direction at both ends, bad quotes are
rejected with a named reason rather than repaired, the liquidity filter applies at entry only
(you must exit what you own), and contracts that expire worthless settle at intrinsic and post
-100% instead of vanishing from the sample.

Local greeks were validated against ThetaData's own: **delta agreed 98.96%** (median error
0.0016), and IV agreed **100% within the tradable |delta| 0.20-0.80 band** (median error 0.0018).

## Not done

Sections 4-6 of the mandate are untouched: the single-leg vs vertical-spread comparison (the arm
is built and committed but not run), the new ThetaData signals (IV rank, VRP, term structure,
skew, flow, GEX), and the live-engine/tracked-book updates. Nothing in the live product has been
changed on the basis of this backtest.
