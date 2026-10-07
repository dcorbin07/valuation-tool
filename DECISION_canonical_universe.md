# Should the canonical backtest move to the corrected universe? — `UNIVERSE-BIAS` part 2

**For Don. Zero trials — every construction here is already registered and this re-measures them
on a corrected input. Nothing is adopted and no public page is changed.**

---

## The short answer

**Your Index is fine. The research headline is not.**

The $10 billion Index tier — the thing you actually run — moves by **−0.40pp** when the universe
is corrected (18.42% → 18.02% net Roth, same vintage). That is the whole effect on the product.

But the **research headline** — "+7.17%/yr top-decile alpha vs the equal-weighted universe,
t 4.38", the number on `/proof` — becomes **+2.83%/yr at t 1.08** on the corrected universe. **It
stops being separable from zero.** And "beat SPY by +9.99%/yr" becomes **+0.77%/yr at t 0.37**.

**My recommendation: do NOT move the canonical panel yet, and do NOT keep quoting the headline as
settled either.** Both of those are addressed below, and the reason it is not a simple switch is
that moving the panel would leave the project with no calibrated bar to judge anything against
until a fresh ~8-hour placebo sweep runs.

---

## What was compared, and why there are three columns and not two

One thing varies between the last two columns. Both are built by the **shipped** builder from the
**2026-10** freeze, cut at the same close, 69 dates 2009-03-27 → 2026-04-09, **all seven themes
alive on both sides**, SPY 16.36% on both.

| | what it is |
|---|---|
| **published** | the tracked `BACKTEST_RESULTS.json` — 2,531 names, data to 2026-07-24. **This is what every public page reads or was copied from.** |
| **restricted** | the *same* `data/backtest` universe, rebuilt on the newer data |
| **corrected** | the full raw universe, same newer data |

`published → restricted` is **newer data**. `restricted → corrected` is **the universe**. Reading
`published → corrected` as "the universe" would blame the universe for two extra quarters.

---

## The headline figures

| figure | published | restricted | corrected | newer data | universe |
|---|---|---|---|---|---|
| panel names | 2,531 | 3,049 | **9,645** | +518 | +6,596 |
| top-decile alpha vs equal-weighted universe | **+7.17%** | +8.19% | **+2.83%** | +1.02pp | **−5.37pp** |
| its t (Newey–West) | **4.38** | 4.66 | **1.08** | +0.29 | **−3.58** |
| excess vs SPY | **+9.99%** | +11.14% | **+0.77%** | +1.15pp | **−10.36pp** |
| its t | **3.77** | 3.45 | **0.37** | −0.32 | **−3.09** |
| excess vs cap-weighted | +10.46% | +11.77% | **+2.20%** | +1.31pp | −9.57pp |
| top decile /yr | 25.31% | 27.50% | **17.14%** | +2.19pp | −10.36pp |
| long-short /yr | +11.04% | +11.91% | **+14.48%** | +0.87pp | **+2.57pp** |
| long-short t (HAC) | 2.62 | 2.80 | **2.12** | +0.18 | −0.68 |
| monotonicity (−1 is perfect) | −0.891 | −0.927 | −0.855 | −0.036 | +0.073 |
| breakeven one-way | 134 bps | 146 bps | **98 bps** | +12 | −48 |
| measured cost one-way | 33 bps | 37 bps | **55 bps** | +3 | +19 |
| **cost margin** | **4.0×** | 4.0× | **1.78×** | — | — |
| Deflated Sharpe | 0.786 | 0.717 | **0.002** | −0.069 | −0.716 |
| PBO (lower is better) | 0.733 | 0.933 | **0.000** | +0.200 | **−0.933** |
| CPCV adopts a tuned weighting? | no | no | **yes** | — | — |
| quarters behind the universe | 29.0% | 26.1% | **37.7%** | −2.9pp | +11.6pp |
| worst quarter | −6.83% | −4.04% | **−14.47%** | — | −10.4pp |

**Two of these move in your favour and should not be lost in the list.** The **ranking** gets
*better*: the long-short spread rises to +14.48%/yr, the deciles stay cleanly ordered, and **PBO
falls from 0.733 to 0.000** — the overfitting statistic the project has always failed now passes,
and CPCV adopts a tuned weighting for the first time.

**But treat that long-short improvement with suspicion, for a measured reason.** `X7` found that
CPCV adoption manufactures about **+1.4 of long-short t out of nothing**, and the corrected run
**adopted** while the published one did not. So the two long-short figures are not on the same
footing, and the honest reading is that the corrected long-short number is the *less* trustworthy
of the two, not the more.

---

## Which public claims no longer hold

Nine of the eleven testable ones. **Eight against us, one for us.**

| claim as a reader sees it | where | verdict |
|---|---|---|
| +7.17%/yr top-decile alpha, t 4.38 | `/proof` (live) | **NO LONGER HOLDS** |
| beat SPY by +9.99%/yr, t 3.77 | `/proof`, `/methodology` | **NO LONGER HOLDS** |
| beat the cap-weighted panel by +10.46%, t 4.29 | `/proof` (live) | **NO LONGER HOLDS** |
| top decile returned 25.3%/yr | `/proof` decile ladder | **NO LONGER HOLDS** |
| breakeven 134 bps vs 33 bps measured — a 4.0× margin | `/proof`, `/methodology` | **NO LONGER HOLDS** (1.78×) |
| Deflated Sharpe about 0.79 | `/proof`, `/methodology`, `/work` | **NO LONGER HOLDS** (0.002) |
| lost to the market in 29% of quarters, worst −6.83% | `/proof` | **NO LONGER HOLDS** (37.7%, −14.47%) |
| the whole ~2,531-name panel | `/methodology`, `hold_horizon.py` | **NO LONGER HOLDS** (9,645) |
| PBO 0.733, failing the <0.50 bar | `/proof` | **NO LONGER HOLDS — in our favour** (0.000) |
| long-short t 2.62 Newey–West | `/proof`, `/work` | SURVIVES (2.12) |
| the deciles are cleanly ordered | `/proof` | SURVIVES (−0.855) |

**And eight more claims were NOT re-measured, so they neither survive nor fail.** I am listing
them because the temptation is to let a claim nobody re-ran read as one that survived: `R1`'s
+6.99%/yr factor alpha, `S22`'s term structure, the score-calibration date counts, the
hold-horizon figures, the options payoff numbers, the dip-survival numbers, the **Index tab's
whole backtested column**, and the live Track Record. Each needs its own re-run.

**The Index tab and the landing page are the important entry in that list**, and the reason they
are unmeasured rather than failing is that `INDEX-BOOK`'s own fidelity gate **refused** to run on
a panel it cannot verify — correctly, and I did not weaken it. What I can say is that the same
construction measured separately reads 18.42% restricted against **18.02%** corrected, so those
tiles move by roughly **−0.4pp**. They survive.

---

## Why the headline falls, in one number

The corrected universe's top decile is **965 names** rather than 155, and it is mostly tiny. On
`data/backtest` the widest book holds a mean **10.9%** of its weight in names under $300M; on the
corrected universe it holds **63.3%**. The composite sorts those names *better* than it sorts
large ones — that is why the long-short improves — but the names themselves return far less, and
trading them costs **55 bps** against 33.

**It is not a data-quality problem, which cuts against the obvious explanation.** The extra names
are *better* documented at the small end than the restricted universe's small end (worst-theme
missing rate 0.342 against 0.445). The restricted universe's small end was simply **pre-selected
for survival**: of the names that were under $300M in 2009 *and later died*, **80.6% are missing**
from `data/backtest`, against 42.1% of the small names that survived.

---

## My recommendation

**1. Do not move the canonical panel to the corrected universe yet.** Not because the corrected
universe is wrong — it is the honest one — but because **every bar the project judges things
against would become meaningless on the day you switched.** All seven calibrated floors come from
`X7`'s placebo sweep on *this* panel. Re-running it on the corrected universe is one command
(`python -m scripts.placebo --panel UNIVERSE_BIAS_PANEL_full.pkl --n 100`) and roughly **8 hours**
of machine time, estimated from the row ratio. Until that runs there is no floor, and a headline
with no floor is worse than a headline with a documented selection caveat.

**2. Do move it after that sweep, and plan for it now.** The corrected universe is the right
research reference. Moving it also means re-deriving every landed figure that rests on the banked
panel, which is a real cost and should be scheduled rather than discovered.

**3. In the meantime, split the authority rather than picking one panel.** The corrected panel is
already the authority for any claim about the **small or wide** end — that is where the defect
bites, and `POOL-SIZE`'s wider-pool recommendation is already withdrawn on it. The canonical panel
stays the reference for the **$10 billion Index**, which the correction barely touches.

**4. The public pages need a decision from you, and I have changed nothing.** The nine failing
claims are not wrong *about the universe they describe* — they are correct statements about a
universe selected on present-day size, which is a real and disclosable limitation. Two honest
routes: add that disclosure, or restate the figures after the sweep. Which one is yours to pick;
the app fixer owns the surfaces either way. Note that `/proof` reads its numbers **live**, so the
day the canonical panel moves those figures change with no code review at all — which is an
argument for deciding the disclosure *before* the panel moves, not after.

**5. The October 22 rebalance is unaffected.** It runs the $10 billion tier on the incumbent rule,
and that is the one thing here the correction leaves alone.

---

## The calibrated floors that would need re-running

All seven, because every one is calibrated on this panel's universe and date count:

| floor | current value | status on a corrected panel |
|---|---|---|
| theme IC *t* | 2.7072 | extrapolation |
| long-short naive *t* | 2.070231 | extrapolation |
| long-short HAC *t* | 2.056680 | extrapolation |
| top-decile alpha margin | 1.8629pp | extrapolation |
| top-decile alpha HAC *t* | 1.826210 | extrapolation |
| PBO (5th percentile) | 19.667% | extrapolation |
| Deflated Sharpe | 0.6637 | extrapolation, **and it moves at every trial count anyway** |

`MB31`'s staleness map does not transfer either: its next adopt-set flip (seed 1017 at equity
`N` = 688) is a property of the *restricted* draws, so a corrected sweep gets its own schedule.

---

*Record: `HANDOFF_edge_audit.md` `UNIVERSE-BIAS` part 2;
`data/free_analysis/UNIVERSE_BIAS_PUBLIC.json` carries the full table and the per-claim verdicts.
The tracked `BACKTEST_RESULTS.json` was never written — verified byte-identical before and after
both runs.*
