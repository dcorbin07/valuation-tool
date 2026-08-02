# A3 — the VRP / put-credit-spread arm: REJECTED (2026-08-02)

Full universe: **55 names, 2016-2025, 2,496 closed put credit spreads** from 119,976 candidate
days. Zero coverage gaps. Every number is net of the touch fill on **both legs both ways** and
commission, on the strategy ported field-by-field from the options-bot.

The adoption gate was committed results-free in `valuation/edge/options_vrp.py` before the
backtest ran (commit 8f15a8c). It **fails on five of its seven arms.**

---

## The headline

    closed trades      2,496
    hit rate           56.4%
    expectancy/trade   -7.99%   (of max risk)
    profit factor       0.28
    net P&L           -$89,467  (1 contract per spread)

    first half  2016-2020   n=1,190   exp = -8.31%
    second half 2021-2025   n=1,306   exp = -7.70%
    -> positive in BOTH halves: FALSE (negative in both)

This is not a marginal miss and it is not a fade. It is negative in **9 of 10 years** (2016 is
+0.4%), in **every IV-rank band**, and on **53 of 55 names** (only WFC and F are positive over
>=10 trades). A result that uniform is a property of the strategy, not of a sample.

### Where the money goes

    BY EXIT REASON       n       mean       avg marks   avg held
      profit (+50%)    1,105    +6.4%          6.6        9 days
      time (21 DTE)      693    -4.0%         10.6       15 days
      stop (-2x)         697   -34.9%          4.1        6 days
      expiration           1   +10.8%          7.0       37 days

44% of trades hit the profit target and earn +6.4% of risk. 28% stop out and lose **-34.9%**.
The arithmetic of that is the whole finding: you win small and often, lose large and often
enough, and 5.5:1 average loss-to-win on a 56% hit rate does not clear.

---

## The three things that could have made this a false reject, and why none of them did

### 1. It is NOT the gap-through model

The 2x stop fills at the real marked price, so a gap books the gapped price. Median stop fills
at **1.33x the theoretical 2x-credit loss** and 12 trades lost the full width. That is a real
cost — but rebooking every stop at exactly 2x credit, which is what a naive backtest does:

    honest (gapped stop fills)      exp -7.99%   pf 0.28
    naive (stop books at 2x)        exp -4.72%   pf 0.40

**Still deeply negative.** The gap model costs 3.3pp of the 8.0pp deficit; the remaining 4.7pp
is there whatever you assume about fills in a spike. `verdict_rests_on_the_gap_model: false`.

### 2. It is NOT a broken fill engine

The no-edge self-test prices every trade as its exact mirror — same strikes, bought instead of
sold. The mirror loses **-31.9%** per trade against the real arm's -8.0%. The two sides are not
both profitable, which is what a fill model paying the tester on both sides of the market would
look like. `both_sides_profitable: false` — the one arm of the gate that passes cleanly.

### 3. It is NOT a data or wiring failure

Coverage is 100% on every input the strategy depends on (iv_rank, atm_iv, short_delta, open
interest, earnings-known). The sanity block is **clean**: no trade loses more than max risk, no
credit sits outside (0, width), every short delta is inside [0.05, 0.45], every entry inside the
25-50 DTE window, and only 0.06% of daily marks needed a no-arbitrage clamp. Median short delta
-0.202 against a 0.20 target; median DTE 36 against a 35 target. The engine traded the strategy
it was told to trade.

---

## What actually kills it: the premium is inside the bid-ask

    median credit at the MID     $0.655
    median credit at the TOUCH   $0.510      (-13.5%)
    median return on risk         10.2%      (credit / width)

    breakeven cost per spread    -$33.25
    commission per spread          $2.60
    entry touch cost per spread   $13.91

The breakeven is **negative**: this loses $33 per spread before a cent of commission. Of that,
roughly $28 is the bid-ask crossed twice on two legs (~$14 each way). A 20-delta $5-wide spread
collects ~$65 of mid credit on these names; giving up ~$28 of it to market makers removes most
of the variance risk premium being harvested.

That is the honest mechanism, and it is specific to **retail single-name credit spreads at the
touch**. It is not a claim that the variance risk premium does not exist.

### Selling richer vol is WORSE, not better

    IV-rank band     n      expectancy    profit factor
      0.50-0.65     877       -6.24%          0.34
      0.65-0.80     648       -8.16%          0.27
      >=0.80        971       -9.45%          0.25

The core VRP intuition — sell when implied is richest — runs backwards here. That is consistent
with the reason the ported bot already sizes DOWN at high IV: rich implied vol is usually
compensation for a real pending jump, not free premium. The entry filter is doing its job and
the job does not pay.

---

## The left tail, modelled honestly

    worst trade            -100.0%   (full width; 12 trades)
    worst 1% mean           -93.4%
    worst 5% mean (CVaR)    -62.5%
    avg loss / avg win       4.55x
    expectancy ex-worst-5%   -5.12%

Negative skew is expected and is not itself the objection — the objection is that removing the
worst 5% of trades entirely still leaves **-5.12%** per trade. There is no tail to excuse here;
the base is negative. The pre-committed 1.5x stress arm fails, as it must.

### As a book, at the ported sizing

    plain (2% risk/trade, vol-scaled, 10 concurrent, 1 per ticker)
      1,251 of 2,496 spreads taken   final equity $20,688 from $100,000
      max drawdown -79.8%            Sharpe -2.50   avg 3.5 concurrent

    with Ledoit-Wolf correlation-aware vol targeting
      757 spreads taken              final equity $59,993
      max drawdown -40.9%            Sharpe -1.67

Vol targeting halves the drawdown and triples the surviving capital — the risk layer works
exactly as intended. It cannot make a negative-expectancy strategy positive, and it should not
be read as doing so.

---

## The correlation finding — the number this exercise existed to produce

**The diversification thesis is CONFIRMED. It does not rescue the arm.**

    monthly correlation with the single-leg arm          +0.246
    correlation in the single-leg arm's DOWN months      +0.036   (52 months)

    Sharpe (monthly, common $1,000-risk-per-trade footing)
      single-leg arm alone      +0.87
      VRP arm alone             -2.01
      combined book             -0.17

Both arms on a common risk footing, P&L booked in the month each trade closed, 113 months
(2016-07 to 2025-11), months with no trades counted as zero.

+0.246 is genuinely low, and +0.036 in the long arm's losing months is close to independence.
A short-vol arm and a long-call arm really are different trades. **But an uncorrelated arm that
loses money does not smooth a book — it drains it.** Combined Sharpe falls from +0.87 to -0.17.

Per year, per $1,000 of risk per trade:

    year      VRP      single-leg    combined
    2016     +692        +20,049      +20,741
    2017    -4,568       +44,552      +39,984
    2018   -47,013       +14,822      -32,191
    2019      -365        +7,216       +6,851
    2020   -47,190       +38,407       -8,783
    2021    -6,690       +15,117       +8,427
    2022   -49,660        -8,626      -58,286
    2023      -616        -3,229       -3,845
    2024   -20,291       +31,969      +11,679
    2025   -23,776          +418      -23,358

Look at the three years this arm was recruited to fix. **2022: the long arm lost 8,626 and the
VRP arm lost 49,660 — it made the worst year six times worse.** 2023 it added a small further
loss. 2025 it turned a flat year into -23,358. The counter-cyclical hypothesis is not merely
unproven, it is contradicted in exactly the years it was aimed at: 2018, 2020 and 2022 are the
VRP arm's three worst years and all three are vol events.

### Short puts across names ARE the same trade in a selloff — measured

    average pairwise correlation of the 55 underlyings' daily returns
      normal days                              0.254
      top-decile implied-vol days (n=251)      0.610      2.4x

The options-bot's own warning is correct and is now a number: ten spreads across ten tickers are
not ten independent bets when it matters. The Ledoit-Wolf layer is right to shrink toward the
constant-correlation prior and right to cap leverage.

**A methodology note, because the obvious version of this test lies.** Selecting the worst 20
days by their own basket return and correlating within them gives **0.233** — LOWER than the
full sample, apparently disproving the effect. That is a conditioning artifact: selecting on the
cross-sectional mean and then correlating the deviations around it compresses the estimate. The
split above is on average ATM IV, which is exogenous to the realised returns. The biased figure
ships in the JSON as `avg_pairwise_corr_worst_days_BIASED` with the caveat attached rather than
being deleted.

---

## Gate scorecard

    1  sample (>=200 total, >=60/half)         2,496 / 1,190 / 1,306      PASS
    2  positive expectancy in BOTH halves      -8.31% and -7.70%          FAIL
    3  profit factor >= 1.20                   0.28                       FAIL
    4a expectancy survives a 1.5x loss stress  more negative              FAIL
    4b book drawdown <= 25%                    -79.8%                     FAIL
    5  no-edge self-test (mirror must lose)    mirror -31.9%              PASS
    6  corr <= 0.30 AND combined Sharpe up     +0.246 but Sharpe 0.87->-0.17  FAIL

**REJECT.** Arm 6 is the instructive one: the correlation half passes and the Sharpe half fails,
which is exactly the case the gate was written to catch. An arm can be genuinely uncorrelated
and still be worth nothing.

---

## What this does and does not say

**Does say:** the deployed options-bot put-credit-spread strategy, run on 55 liquid large caps
with real NBBO on both legs at the touch, lost money over 2016-2025 — robustly, across years,
names and IV regimes, and not because of the gap model or the fill engine. Roughly $28 per
spread of a ~$65 mid credit is consumed by crossing two bid-ask spreads twice.

**Does NOT say:** that the variance risk premium is not real. It says the premium available on
*these instruments at retail touch fills* is smaller than the cost of harvesting it. Index
options (SPY/QQQ), wider spreads with better credit-to-width ratios, or genuinely passive
mid-ish fills are all untested here and none is refuted by this.

---

## Fill-quality diagnostics — and why they close the question rather than open it

Aggression 1.0 is the touch on both legs both ways, and it is the only headline. Lower values
are the diagnostic `options_fill` already declares: "provided ONLY as a diagnostic to show how
much of a result is spread assumption; it is never the headline number." Each row is a full
independent 55-name run.

    aggression      n       hit     expectancy   profit factor   book final   combined Sharpe
    0.00 mid      2,609   73.7%     +0.13%          1.02         $104.1k         +0.77
    0.50 half     2,522   65.0%     -4.37%          0.50          $32.9k         +0.22
    1.00 touch    2,496   56.4%     -7.99%          0.28          $20.7k         -0.17

Expectancy is close to linear in aggression, so break-even sits at roughly **1.5% of the way
from the mid to the touch** — an essentially perfect mid fill on both legs, both ways, every
time. The live bot's own 0.95x-mid resting order is more aggressive than that.

**This is the finding that settles it.** The natural objection to the headline — "you charged it
two full spreads on two legs, of course it lost" — is answered by the top row: at a fill nobody
can achieve, the strategy is *break-even*, not good. PF 1.02 against a 1.20 bar, negative in the
first half, and it still LOWERS the combined Sharpe (0.87 -> 0.77). There is no premium being
lost to execution here, because there is no premium.

The hit rate moving 73.7% -> 56.4% as fills worsen is the mechanism in one number: crossing the
spread pushes the +50%-of-credit target out of reach and pulls the -2x stop closer, converting
winners into stops.

---

## Standing caveats

- **One sample.** 55 large caps, one 2016-2025 window, the same window the long arm was fitted
  and measured on. Nothing here is out-of-sample in the way a forward track would be.
- **Earnings coverage is partial.** Sharadar EVENTS code 22 gives ~2.83 announcements per
  ticker-year against ~4 actual, so some earnings were not filtered and this book carries MORE
  event risk than the live bot would. Wrong in the conservative direction; 29,818 candidate days
  were skipped by the filter that did fire.
- **Daily closes only.** The stop is pessimistic on slow losers (which would have been closed
  intraday nearer 2x) and about right on genuine gaps. The counterfactual above bounds how much
  that matters: 3.3pp of an 8.0pp deficit.
- **American exercise, assignment, pin risk and borrow are not modelled.** All three would make
  the result slightly worse, not better.
- **`credit_target_fraction_of_mid` is not modelled.** The live bot rests at 0.95x mid; this
  takes the touch on both legs. That gap is the subject of the fill-quality diagnostics.
