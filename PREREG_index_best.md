# PRE-REGISTRATION — INDEX-BEST: which construction should the Valquo Index be?

**Committed ALONE, markdown only, zero `.py`, BEFORE any arm is scored and before any runner
exists.** This file is a strict git ancestor of every commit that computes an outcome for arms
2, 3 or 4. **Three equity trials are booked in a SEPARATE commit before that runner exists**, so
the booking cannot be read as having followed a result.

**DON'S RULING, 2026-10-03, quoted because it is the licence for the whole item:** *"the Valquo
Index is whatever construction gives the best NET-OF-TRADING-COST return in a Roth (no tax);
taxable after-tax figures are reported for transparency only. Smaller companies are allowed if
they win."* It **supersedes `INDEX-UNIVERSE` and the scout's `IC6`** — neither of which has a
ledger row, and `PREREG_DRAFT_ic6_large_cap_cut.md` is a scout draft that never ran.

**ADOPTS NOTHING.** The winner is **routed to Don** for adoption at the 2026-10-22 rebalance,
which is a **vintage event**. Nothing here ships.

---

## 0. Counter, and the trial charge

`by_domain` read at the time of writing: **equity 252, options 310, unified 0, infra 20**;
`rows_fixed_not_counted` 88, `rows_malformed` empty. Equity hurdle √(2·ln 252) = **3.3255**; at
255 it is **3.3314**. These are quoted as the HLZ hurdle only, not as a bar this item uses.

**THREE equity trials, one per CHALLENGER — arms 2, 3 and 4. Arm 1 charges ZERO.** Arm 1 is the
incumbent reproduced on machinery this project has already validated (`INDEX-BOOK`, `ceffd04`);
it tests no hypothesis and cannot come back the other way, which is the `S25`/`MB3`/`X7RECON`
class. The counter-argument is that arm 1 is the comparator every challenger is paired against,
so it is load-bearing — the distinction is that a comparator which cannot be selected over
adds no degree of freedom (`MB1-SEL`), and **overstating `N` is the safe direction** (`MA6`).

**`MB31`: no permutation floor can move here.** The next adopt-set flip is seed **1017 at equity
`N` = 688**; at 255 the adopt set is unchanged, so every calibrated floor in the record is still
current. **This item uses none of them anyway** — see §5.

---

## 1. Three premise corrections, ALL made before any outcome exists

These are the reason the register is worth reading. Each is measured, and each changes an arm.

### 1a. There is NO point-in-time liquidity measure, so "most liquid" CANNOT be built as stated

`B13` is `PARTIAL — BLOCKED ON DATA` for exactly this: the price export is `date,close` and
carries no volume. **Measured, not inherited:** the only volume on disk is
`data/bulk/prepared/bars/*.pkl` — **502 tickers, 486 of them in the panel, 19.20% of the panel's
2,531 names**, reaching a median **24.75%** of each cross-section (min 22.34%, max 28.99%), and
**starting in 2016** against a panel starting 2009. It is also the OPTIONS MINER's cache, i.e.
**today's optionable survivors** — so using it to SELECT would import survivorship bias into the
universe definition, which is worse than any proxy's imprecision.

**THE PROXY IS POINT-IN-TIME MARKET CAP, and its fidelity cost is measured rather than asserted:
the within-date Spearman between market cap and 63-day dollar ADV is 0.7119 (p05 0.6824, p95
0.7486) on the rows where real volume exists.** So a cap screen shares about half the rank
variance of a true liquidity screen and **is a materially different screen**. Two directions are
stated because they cut opposite ways: that subset is the LIQUID end of the universe, and range
restriction usually DEPRESSES a correlation, so the full-universe figure is plausibly higher —
a direction, not a measurement, and it is not used as one. `INDEX_BEST_LIQ_FIDELITY.json`,
a CONTROL run before this register (`MB1-SEL`: it can only block, so it charges nothing).

### 1b. The live scan is NOT the binding constraint — the PANEL is

The brief says *"the ~1,500 most liquid names the live scan ranks"*. **Measured from the live
payload: the scan scores 1,809 names, of which 861 clear $10B, producing the 86-name book.**
The panel's cross-section runs **1,471 / 1,557 / 1,954** (min / median / max). **So the live scan
ranks MORE names than the panel carries on a median date**, and a top-1,500 screen keeps
**96.34%** of the median cross-section and is **completely inert on 3 of 69 dates**.

**Consequence, stated in advance: arm 2 is expected to be CLOSE to arm 4, and if it is, that is
the finding rather than a failure** — it would mean the all-cap research decile is essentially
reachable by the live scan, which is the thing Don's arm 4 was labelled a ceiling for fear it
was not.

### 1c. …but the screen bites TWICE AS HARD on the BOOK as on the UNIVERSE, so arm 2 is not a duplicate

A 3.66% cut to the universe is not a 3.66% cut to the book, because the composite tilts small and
the names the cap screen removes are the smallest. **Measured on composition only, with no
forward return touched: the top-1,500 screen removes a median 7.69% of the all-cap decile's BOOK
against 3.66% of the universe — 2.1× harder — and on the worst date it removes 42.0%** (book
survival median 0.9231, min 0.5798, max 1.0000). **That is why arm 2 is worth a trial.**

---

## 2. The arms

**ALL FOUR share one construction and differ in ONE knob each**, and all four **CALL
`valquo_index.build_index`** rather than restating the tier filter, the band, the score weighting
or the 8% cap (`B7`). Shared: score-weighted on the percentile-ranked composite
(`screen.py:344`), 8% cap, quarterly (63 trading days), 30% no-trade band, flat 1/7 over the
seven DEPLOYED themes (imported from `scripts/sector_neutral_rerun`, never retyped), scored on
`panel_corrected_69d.pkl`, net of the shipped size-aware cost table `one_way_cost_bps`.

| arm | universe | book | trials |
|---|---|---|---|
| **1 — incumbent** | $10B tier, NOMINAL | top decile of the tier | **0** (reproduction) |
| **2 — liquid decile** | top 1,500 by point-in-time market cap | top decile | **1** |
| **3 — liquid 25** | top 1,500 by point-in-time market cap | **top 25** (`top_n=25`) | **1** |
| **4 — all-cap ceiling** | the whole scored cross-section | top decile | **1** |

**Arm 1 must reproduce `INDEX-BOOK`'s `A_served` at max |Δ| 0.000e+00 or the item ABORTS** before
any challenger is read. That is the fidelity gate, and the period count is gated with it
(`MB21`'s `C1` once scored a perfect zero on an empty frame by comparing nothing).

**A PRE-REGISTERED CAVEAT ON ARM 3, because "the same 30% band" is NOT the same rule across
arms.** The band's exit rank is a fraction of the UNIVERSE, so for arm 1 it is ~3× the book
(enter top 10%, exit at 30%) and for arm 3 it is ~**18×** (enter top 25 of ~1,500, i.e. the top
1.7%, exit at 30%). `after_tax_backtest` carries an `exit_mult` for exactly this reason — its own
comment calls it *"the only one meaningful for a fixed-N book"* — and `build_index` does not
expose it. **Arm 3 is run with the 30% band AS DON SPECIFIED**, and its turnover and period-to-
period book overlap are reported, so a win driven by a near-frozen book is visible rather than
hidden. `S14-WIDTH` measured a book FREEZING at a wide enough band; this is the shape to watch.

**`B17`'s warning is adopted in advance for arm 3: the top-25 book is the noisiest number this
project publishes.** Its instability is reported with it — both halves, Sharpe, drawdown — and
a win by arm 3 is to be read with that attached.

---

## 3. Metrics

**PRIMARY: net-of-trading-cost Roth return (no tax), annualised, and its excess over SPY.** The
Roth figure is `after_tax_backtest` run at `short_rate=0, long_rate=0` — the identical lot path,
rates as the only knob — so cost treatment is common to every arm by construction.

**PAIRED AGAINST ARM 1**, per period, in BOTH halves, with a Newey–West HAC *t* at lag 1.
**Halves: the 69 periods split at the median with the BOUNDARY PERIOD EMBARGOED** — early =
periods 1–34, late = 36–69, period 35 dropped from both. Fixed here, before any outcome.

**REPORTED FOR EVERY ARM, no verdict attached:** Sharpe, max drawdown, annual turnover, realised
one-way cost in bps, book size, **taxable after-tax return at 40.8% short / 23.8% long with FIFO
lots** (transparency only, per Don's ruling), and capacity per `P1`/`P2`.

**COSTS: the size-aware shipped table**, 4 bps above $200B down to 150 bps below $100M. **What a
small-cap-heavy book pays is required output**, not a footnote: `INDEX-BOOK` measured the $10B
book at **9.58 bps** realised against the all-cap decile's **33.35 bps**, and `P1` measured
**87 bps at $1M** on the top-25 all-cap book. A challenger that wins gross and loses net is the
outcome this cost model exists to catch.

**THE NO-DIVIDEND LIMIT TRAVELS WITH EVERY TAXABLE FIGURE** and runs AGAINST the taxable arm: the
panel's forward returns are price-only, so dividend income is absent from the gross figure and
dividend tax is absent from the after-tax one. It understates a real taxable investor's drag.

---

## 4. THE PICK RULE, pre-committed

> **The winner is the arm with the HIGHEST NET ROTH RETURN among the arms that (a) beat arm 1 on
> net Roth return in BOTH halves and (b) are buildable from the live scan. If no arm qualifies,
> ARM 1 STANDS.**

**"Buildable from the live scan" is fixed here and is not a judgement made later:** an arm
qualifies if its universe is defined by a quantity the live scan computes for every name it
ranks. Arms 1, 2 and 3 qualify by construction (market cap). **Arm 4 does NOT qualify** — it is
the whole panel cross-section, labelled a CEILING, and it may win the ranking and still not be
adopted. If arm 4 is the highest and fails (b), that is reported as *"the ceiling is higher than
anything we can serve"*, which is a finding about the gap and not a recommendation.

**Ties are broken toward arm 1** (the incumbent, i.e. toward not changing anything).

---

## 5. Power — stated BEFORE any margin, and the reason there IS no margin

`MB22` / `RUN_RULES` A11: `MDE50 = crit × se`, `MDE80 = (crit + 0.84) × se`.

**EX-ANTE, from arm 1's PUBLISHED period series** (`INDEX_BOOK.json`; the incumbent, so no
challenger outcome is read): 69 periods, sd **0.085309**. The paired se depends on the
correlation between a challenger and arm 1, which is unknown until the run, so it is bracketed:

| assumed ρ | paired sd | se | **MDE50 /yr** | **MDE80 /yr** |
|---|---|---|---|---|
| 0.80 | 0.053954 | 0.006495 | +5.20pp | **+7.38pp** |
| 0.90 | 0.038151 | 0.004593 | +3.67pp | **+5.22pp** |
| 0.95 | 0.026977 | 0.003248 | +2.60pp | **+3.69pp** |
| 0.99 | 0.012065 | 0.001452 | +1.16pp | **+1.65pp** |

**THIS IS THE MOST IMPORTANT SENTENCE IN THE REGISTER. Even at ρ = 0.95 the design detects only
+3.69pp/yr at 80% power, and the incumbent's ENTIRE edge over SPY is +1.95pp/yr. So this design
CANNOT establish that one construction is statistically better than another at any difference
the project is likely to see.**

**That is precisely why the pick rule carries NO THRESHOLD.** It is a RANKING plus a SIGN
condition — highest net return among those positive in both halves — and it invents no
uncalibrated bar. `V2G` and `R1-VAR` established that **no calibrated floor exists for a paired
within-panel difference**; every critical value quoted anywhere in this item is therefore
**LABELLED UNCALIBRATED**, including the 2.0 used in the table above. **The realised paired HAC
se is measured per arm and reported with its own MDE** (`MB8`: an se may never be borrowed across
constructions).

**So the honest claim available to the winner is "best in this sample", never "proven better".**
§8 fixes the sentence Don may quote.

---

## 6. Void conditions

1. **No grid.** The four arms above and nothing else — no third book size, no second cap
   threshold, no band sweep. Adding an arm after seeing a result voids the item.
2. **The pick rule may not be restated after any outcome is read.** `W-28`'s closing lesson: a
   pre-committed rule may not be relaxed after watching it fail.
3. **No arm may be re-specified to fit the data.** If an arm is infeasible it is reported
   infeasible.
4. **Nothing is adopted here.** An eligible winner is recorded **ELIGIBLE, NOT ADOPTED** and
   routed to Don; adoption is a vintage event and his call.
5. **The taxable figures carry no verdict** and may not be used to pick (Don's ruling).
6. **Arm 1 must reproduce `INDEX-BOOK` exactly** or the item aborts unread.
7. **No claim of statistical superiority** may be made for the winner. §5 forbids it in advance.

---

## 7. Expectations, registered now and scored afterwards

1. **Arm 1 stands — no challenger beats it in both halves: 50/50.** The record points both ways
   and says so: `regime_split` measured the edge **strongest in large caps**, which favours arm 1,
   while `U7` measured the top tier compressing the cross-section toward a pure size sort, which
   favours a wider universe. `IC6` ranked itself last for exactly this conflict and could not
   resolve it in advance. Neither can this.
2. **Arm 4 posts the highest GROSS return of the four: 75/25** — it holds the small names, and
   `INDEX-BOOK` measured the size premium at −4.18pp against the $10B tier, i.e. +4.18pp for
   holding it.
3. **Arm 4's NET advantage is at least a third smaller than its gross one: 70/30** — 33.35 bps
   against 9.58 bps realised, on ~2.6× turnover.
4. **Arm 2 lands between arms 1 and 4 and nearer arm 4: 65/35**, since it removes a median 7.69%
   of arm 4's book.
5. **Arm 3 has the widest half-to-half spread of the four: 80/20** (`B17`).
6. **Arm 3's turnover is LOWER than arm 2's: 60/40** — the 18× band should make it sticky; the
   opposite reading is that a 25-name book churns more, and the measurement decides.
7. **No arm's paired difference against arm 1 clears |t| = 2.0 in both halves: 70/30.** §5's
   arithmetic, and it would make the ranking the only usable output.

---

## 8. The sentence for Don, fixed in advance of knowing the winner

Whatever wins, the quotable claim is bounded by what this design can support. The template, with
only the bracketed figures to be filled from the result:

> *"On an 18-year point-in-time backtest of 69 quarterly rebalances, this construction returned
> **[X]%/yr net of modelled trading costs in a tax-free account**, against **[Y]%/yr** for SPY
> over the same window. This is an IN-SAMPLE backtest on a single panel, not a forward test; it
> is net of trading costs and assumes no tax; and the difference between this construction and
> the one we serve today is **NOT statistically separable** on this sample."*

**What may NOT be said:** that the winner is proven better than the incumbent; that the figure is
a forward result; that it is achievable after tax in a taxable account (§3's taxable figures say
otherwise); or that it is achievable at size (capacity is an upper bound, `P1`).

---

## 9. NOT done, named so it is not mistaken for done

* **No liquidity screen is built**, because none can be built point-in-time (§1a). Every arm's
  universe is a MARKET-CAP universe wearing a liquidity label, and the label is corrected in the
  artifact.
* **No inflation-adjusted tier.** $10B is nominal because the live code is nominal.
* **`regime_split` is not re-run** and the large-cap-edge finding is not re-measured here.
* **No forward-track claim.** This is a backtest column; the contract's forward test is untouched.
* **`IC6` is superseded, not executed** — its own arm (a single lowered cut) is not run, and this
  register does not answer where the tier should be cut if the tier survives.
