# PRE-REGISTRATION — `V6-OPT`: cash-secured puts on healthy dips

**Registered 2026-08-13, before the instrument exists.** Committed **ALONE** — one `.md`, zero
`.py` — and a strict git ancestor of every commit that measures anything.

**Two stages.** Stage 1 is **DESCRIPTIVE, no arms, no verdict about the world**. Stage 2 is a
backtest that runs **only if stage 1 clears a gate fixed in this file before stage 1 runs**. The
point of writing both now is that **stage 2 must not be designed after seeing stage 1's numbers.**

**ADOPTS NOTHING.** No live code path changes. Frozen caches on both sides; no re-mine.

---

## 0. What unlocks this, and the four priors that constrain it

`V6-B` (register `PREREG_v6b_dip_survival.md`, committed alone at `dc5ae98`) made `V6-OPT`
conditional on its `M1` separating, and **`M1` separated**: among 20%+ dips the HEALTHY set — V6's
floors unchanged — falls a further 20% within 126 trading days on **32.51%** of occasions against
**43.35%** for the unhealthy set, a **10.84pp absolute / 25.0% relative** reduction at HAC *t*
**−10.58**, replicated in both halves (**−9.064pp**, **−11.515pp**).

**Four priors travel with that unlock, and three of them are negative.**

**(a) THE THREE CAVEATS V6-B ATTACHED, quoted rather than paraphrased.** The claim is about
**falling further, not defaulting** (M2, the actual bankruptcy metric, is **VOID on power** at 42
events against a floor of 60 — *none of its numbers are quotable*); it is **weakest in megacaps**
(−3.787pp in the largest quintile against −14.287pp in the smallest); and **V6 already showed this
same population carries no return edge** (four nulls), so a CSP case rests on **the risk profile
and the premium, never on expected appreciation**.

**(b) THE NEAREST PRIOR IS `A3`, AND IT WAS REJECTED DECISIVELY — the task's framing does not
mention it, and it is more relevant than the frame the task does discuss.** `HANDOFF_vrp.md`
(2026-08-02) tested a **put-credit-spread** arm on **this same options data**: 20-delta short leg,
25–50 DTE, entered on IV rank, 2,496 trades over 55 names and 10 years. **Expectancy −7.99%/trade,
profit factor 0.28, book $100k → $20.7k, max drawdown −79.8%, negative in 9 of 10 years, on 53 of
55 names, and negative in both halves.** Three of its findings bind here:

1. **"Selling RICHER vol is WORSE"** — IV rank ≥ 0.80 gave **−9.45%** against **−6.24%** at
   0.50–0.65. **So "post-dip implied vol is elevated" is not by itself evidence of an
   opportunity. That exact thesis was tested on this universe and ran backwards.** This is why
   the gate in §3 is *not* "is IV elevated".
2. **The ceiling is break-even.** At a perfect mid-to-mid fill the arm is PF **1.02**; the
   deficit is not an execution artefact, it is *"a strategy with no premium left after the market
   has priced it, and execution then makes it negative."*
3. **Its three worst years (2018, 2020, 2022) are all vol events** — *"the counter-cyclical
   hypothesis is not merely unproven, it is contradicted in exactly the years it was aimed at."*
   A post-dip CSP is a sell-into-fear trade, so this is the same corner of the world.

**What A3 does NOT refute, in its own words:** index options, wider spreads, genuinely passive
fills — and, not being in its scope at all, **any conditioning on a drawdown or on financial
health**. A3 sold vol because vol was high. `V6-OPT` proposes selling vol on a population whose
**realised** tail is measurably thinner. Those are different claims.

**(c) THE DEAD-ENTRY FRAME (`R2`) DOES NOT APPLY, AND THIS IS STATED DELIBERATELY RATHER THAN
INHERITED.** `R2`/`U1-SPLIT` found the live options **alert** loses to random entry by
**−5.0640pp**, and `O13` found that gap is entirely a within-bin rate effect. That verdict is
about **the alert's day-selection mechanism**. `V6-OPT`'s entry is not the alert — it is a
quarterly panel date on which a name is in a ≥20% drawdown and clears V6's health floors. **No
part of the alert's machinery is in this path.** The dead-entry result therefore neither condemns
nor endorses it, and **the random-entry control in §5 is what settles the question for this
mechanism, on its own evidence.** Equally: *nothing here may be read as re-opening `R2`.*

**(d) SIZING, from `O11`.** A book with **+3.27%/trade positive expectancy ended at $37,059 from
$50,000** at a concurrency cap of 10, because alerts cluster and the edge lives in the crowded
weeks. **Per-trade expectancy is not a verdict.** Stage 2's verdict requires survivability, §4.4.
A3 independently reached the same place: average pairwise correlation rises **0.254 → 0.610** on
top-decile implied-vol days, so *"ten short-put spreads across ten tickers are not ten independent
bets when it matters."*

---

## 1. Premise findings — measured BEFORE this register, none of them an outcome

Every number in this section is a fact about what is on disk or about the coverage of an
already-decided population. None is a hypothesis and none is scored. Reproduce with
`python -m scripts.v6opt_premise`; artifact `data/free_analysis/V6OPT_PREMISE.json`.

### 1a. A DEFECT IN MY OWN PRIOR SESSION: THE CHAIN CACHE IS NOT 100% CALLS, AND `U6` WAS CLOSED PARTLY ON THAT CLAIM

Session 37's `DESIGN_u4_u6_u8.md` closed `U6` (the same CSP idea, entered off the equity book)
`DESIGN-RECORDED — NOT BUILDABLE ON DATA WE OWN`, giving two blockers. The second reads:

> `U6`'s entry leg is a cash-secured **put**. The banked options book is `opt_right == "call"` on
> **3,870 of 3,870 rows** — 100% calls, measured. The mined cache was built for a long-call alert
> strategy, so there is no banked put-chain history to replay a CSP against.

**The measurement is right and the inference from it is wrong.** 3,870-of-3,870 calls is a fact
about the **traded book**. It is not a fact about the **chain cache**, and the cache was never
checked. Measured now, on 40 randomly sampled tickers and 2,577,501 contract-days:

| | measured |
|---|---|
| puts in the chain cache | **1,288,750** |
| calls | **1,288,751** |
| **put share** | **exactly 0.5000** |
| tickers with **zero** puts | **0 of 40** |

The cache stores **full chains, both rights**, with `bid`, `ask`, `volume` and `open_interest`.
**So the put-history blocker does not exist.** `U6`'s *other* blocker — 1.81% chain coverage of
the equity book's top-decile entries — was measured against a different population and is not
disturbed by this; but the row was closed on both, and one of the two was false. **`U6`'s ledger
row and the memo are corrected as part of this session's deliverable, against my own prior
result.** (`RUN_RULES` 3.)

### 1b. THE INSTRUMENT ALREADY EXISTS AND IS THE SHIPPED ARITHMETIC

`data/options_derived/<TICKER>/<TICKER>-daily.pkl` is a **precomputed daily surface**, 2,515 rows
per full ticker spanning **2016-01-04 → 2025-12-31**, carrying `spot`, `atm_iv_14/30/60`,
`atm_iv_front`, `skew_25d`, `iv_call_25d`, `iv_put_25d`, `iv_rank`, `iv_pct`, `put_oi`, `put_vol`,
`pc_oi`, `oi_coverage`. It is produced by the shipped `options_greeks`. **502 tickers, 387 with all
ten years, 392–501 per year.** Per-year contract files carry every contract-day with `iv`, `delta`,
`dte`, `moneyness`, `mid`, `spread_frac`, `open_interest` — so a **real** 25-delta put with a
**real** quoted spread is selectable, which is what `O18` says decides the answer.

**TWO COLUMN-NAME TRAPS ARE NAMED NOW because `U2` was caught by one.** `skew_25d` **is exactly**
`iv_put_25d − iv_call_25d` (U2 measured max |Δ| **0.000e+00** over 217,706 rows), so it and "the
put-minus-call spread" are **one column, not two**, and may never be reported as independent
evidence. And `term_slope_60_30` is **NOT** `O16`'s validated `term_slope`; it is not used here at
all.

### 1c. COVERAGE FORBIDS A FULL-PANEL GATE — AN IMPOSSIBILITY, NOT A POWER CAVEAT

V6-B's dip population is **37,982 dipped `(date, ticker)` rows** on the panel's 69 quarterly dates
(10,189 healthy). Joined to the derived surface by `(ticker, year)`:

| | measured |
|---|---|
| dipped rows with surface coverage | **4,855 of 37,982 = 12.78%** |
| healthy covered / unhealthy covered | **1,631 / 3,224** |
| panel dates with ≥1 covered dip | **40 of 69** |
| dates with **zero** covered dips | **29 — 28 of them EARLY (2009-01-15 … 2015-10-19) and 1 late (2026-01-28)** |
| covered dips per date | median **48**, min 0, max **346** |

**This is `S18`'s, `U2`'s and `U3`'s situation for the fourth time**, and the same replacement is
adopted: **every split is of the COVERED SUBSAMPLE — 40 dates**, split at its median with the
boundary date embargoed, giving halves of **20 and 19**. A pass on 20-date halves is not the same
object as a pass on 40-date halves, and this is stated before any result.

### 1d. THE SIZE TILT BINDS AGAINST THE CLAIM, AND IT IS THE MOST IMPORTANT PREMISE FACT HERE

Covered dips have a **median market cap of $17.92bn against $2.17bn for uncovered — a 8.26×
tilt.** Options are mined on liquid large caps, so **the only population on which a CSP study can
be built is the large end** — which is **precisely where V6-B measured M1's separation to be
weakest (−3.787pp, against −14.287pp in the smallest quintile).**

**Consequence, fixed now: the risk asymmetry this trade is built on is roughly a quarter as large
on the tradeable population as the headline `M1` number.** Any stage-2 result must be quoted
against **−3.787pp**, never against **−10.84pp**, and a favourable stage-2 result may **not** be
generalised to the small-cap end where the separation is largest and no options exist.

---

## 2. STAGE 1 — DESCRIPTIVE. Six measurements, no arms, no verdict about the world

**Population:** the **4,855 covered dipped rows** of §1c, labelled `HEALTHY` / `UNHEALTHY` by V6's
floors **imported, never restated** (`quality` z > 0 **and** point-in-time `health` ≥ 50). **Re-tuning
a floor is void condition 8.4**, as it was in V6-B.

**Observation date** is the panel rebalance date `d`. All surface reads are on the last surface row
dated **`<= d`**, never after — the point-in-time rule, and C3 counts violations.

| id | measurement | why it is here |
|---|---|---|
| **D1** | `atm_iv_30` at `d` versus **the name's own trailing 252-day median** `atm_iv_30`, strictly before `d`. Reported as a ratio and a difference. Shipped `iv_rank` reported beside it as an independent second measure. | the task's *"how elevated vs the name's own baseline"* |
| **D2** | the path of `atm_iv_30` over the **next 30 trading days**, indexed to its value at `d`; reported as a curve with a half-life where one is computable | the task's *"decay curve over 30d"* |
| **D3** | `skew_25d` at `d`, and versus its own trailing 252-day median | the task's *"put-skew state"* |
| **D4** | the **real contract a CSP would sell**: the put with `delta` nearest **−0.25** among `30 <= dte <= 45`, reporting its `mid`, `spread_frac`, `open_interest`, and the **credit as a fraction of the strike**, annualised | *"enough fear premium … to pay for selling puts"* — the actual premium, from real quotes |
| **D5** | **THE DISCRIMINATOR.** The healthy-minus-unhealthy gap in D1, D3 and D4, set beside M1's own realised risk gap on the same covered rows | see below |
| **D6** | **VRP.** `atm_iv_30` at `d` minus the **realised** close-to-close volatility of the underlying over the following 30 trading days, annualised | whether the elevated implied is already justified by what follows |

**D5 IS THE POINT OF STAGE 1, AND IT IS WHY A3 DOES NOT SETTLE THIS IN ADVANCE.** A3 established
that selling vol *because it is high* loses on this universe. The question that survives A3 is
different: **does the option market price the healthy/unhealthy distinction that `M1` measures?**
If fear is priced roughly alike across healthy and unhealthy dips while the realised tail differs,
that is a **cross-sectional** mispricing and A3 says nothing about it. If instead healthy dips
already carry visibly cheaper vol, the market has priced `M1`, there is nothing to harvest, and
the branch closes.

**M1 IS RE-MEASURED ON THE COVERED ROWS** rather than quoted from V6-B, because §1d predicts it
will be much smaller here. **That re-measurement is a control, not an arm** — it re-runs a
settled metric on a subsample and charges no trial.

**Stage 1 returns no verdict about the world.** It returns a **gate decision** (§3).

---

## 3. THE RICHNESS GATE — fixed here, before stage 1 runs

**All three must hold, on the HEALTHY covered set, in BOTH halves of the covered subsample.**

* **G1 — THERE IS SOMETHING TO SELL, NET OF COSTS.** The median D4 credit, after charging the
  quoted half-spread at the **shipped** `options_fill` aggression **1.0** (sell the bid), is
  **> 0** and is **≥ 0.50% of the strike** for a 30–45 DTE put. *Rationale, fixed now:* below
  roughly 0.5% of notional per ~6 weeks the premium cannot survive one assignment in twenty at
  a −20% further fall, which is the loss rate `M1` itself measures.
* **G2 — THE MARKET HAS NOT ALREADY PRICED THE DISTINCTION.** The healthy set's D1 elevation is
  **≥ 75%** of the unhealthy set's. *Rationale:* if healthy dips carried materially cheaper vol,
  the market would already be paying less exactly where the risk is lower and the `M1` asymmetry
  would be priced out. 75% is a judgement fixed in advance, **not calibrated** (§3.1).
* **G3 — THE PREMIUM IS NOT MERELY FAIR.** Median **D6 (VRP) > 0** on the healthy set. If the
  elevated implied is fully justified by the realised volatility that follows, there is no
  premium to harvest and A3's result should be expected to repeat.

**GATE OPEN** = all three, both halves. **GATE CLOSED** = anything else, and then **stage 2 does
not run**, `V6-OPT` closes at stage 1, and the closure is recorded as **measured** rather than as
a design opinion. **Ambiguous against any bar is a CLOSE** (`RUN_RULES` A6).

### 3.1 EVERY BAR IN §3 IS UNCALIBRATED, AND IT IS LABELLED SO EVERYWHERE IT APPEARS

`X7` calibrates a theme-IC floor, a long-short *t* floor, a top-decile alpha margin, a PBO bar and
a Deflated Sharpe bar — **on a decile-book equity panel**. **None of them is this object**, and
none is quoted. The 0.50%, the 75% and the VRP sign are **conventions fixed in advance to stop the
gate being chosen after the fact**, and they carry no claim to a false-positive rate. **A gate that
opens is not evidence of anything; only stage 2 can be evidence.**

---

## 4. STAGE 2 — the backtest, designed now, run only if the gate opens

**Entry.** On each covered dip date `d`, for each **HEALTHY** dipped name, sell the D4 contract —
the put with `delta` nearest **−0.25**, `30 <= dte <= 45`, requiring `open_interest >= 100` and
`spread_frac <= 0.25` (**the project's own quote-sanity bar**, not the options-bot's 10%; A3
measured that loosening 10% → 25% *admitted 28% more trades and made its arm worse*, so the looser
bar is the conservative choice here).

**Exit.** Held to **expiry**. Assignment if the underlying closes below the strike; the assigned
stock is then **marked at expiry**, not carried, so the arm is a closed-form per-trade result.
No profit target, no stop, **no exit grid is swept** — `S23` paid for that lesson and
`sweep_hold_params`-style selection is void condition 8.5.

**Fills.** Headline at the shipped `options_fill` **aggression 1.0** — sell the bid, buy the ask —
**the same aggression A3's headline used**, so the two are comparable. `O18`'s measured **ρ =
0.6743** ships as a **declared diagnostic beside it and never as the headline**, and `O18`'s own
rule travels with it: the availability term is **selected** and may never be quoted as a saving.

**Sizing.** Flat one contract per slot, cash-secured at the strike, **concurrency caps {10, 50}**
— `O11`'s own grid — refusing when full.

### 4.1 THE FOUR MANDATORY CONTROLS

* **C-A — CSPs ON UNHEALTHY DIPS. The discriminator, and the one that decides.** Identical rule,
  identical dates, opposite label. **If the healthy arm does not beat this, the health floors are
  doing no work and the trade is just short vol** — which A3 already rejected.
* **C-B — THE STOCK EXPRESSION.** Buy the shares at `d` instead, held to the same expiry.
  Answers *"why the option rather than the stock"*, which V6's four nulls make a live question.
* **C-C — RANDOM ENTRY, ≥ 5 SEEDS.** Same names, same contract-selection rule, random dates,
  five seeds minimum, **the sign test carrying the verdict** — the standing rule from `R2`, where
  a single seed flipped the reading.
* **C-D — THE NO-EDGE MIRROR.** Every trade priced as its exact mirror (the same put **bought**).
  Both sides must not be profitable. A3's one cleanly-passing gate arm, imported.

### 4.2 What counts as REAL (stage 2), committed now

All four, and any one failing is a REJECT:

1. Positive expectancy per trade at aggression 1.0, **in both halves**;
2. **beats C-A** (healthy minus unhealthy) in **both halves**;
3. **beats C-C's five-seed distribution** on the paired name-year **sign test**;
4. **survives §4.4.**

### 4.3 THE ASYMMETRY IS DECLARED IN ADVANCE, as `U3` had to

The covered sample holds **one** genuine crash (COVID 2020Q1, the trough `S10` measured at index
44 of 69) and A3's worst years are vol events. **A decisive REJECT is therefore available** — it
is a failure of sign, measurable across all 40 covered dates — **while a decisive ADOPT is not**,
because a short-vol book's whole risk is concentrated in crash quarters and this sample contains
one. **A clearing arm is recorded `ELIGIBLE-BUT-UNRESOLVED`, never `ADOPTED`**, with its
crash-quarter result quoted beside it. **Nobody may read a rejection here as evidence that
cash-secured puts do not work.**

### 4.4 SURVIVABILITY DECIDES, NOT EXPECTANCY (`O11`)

The arm must not produce a **max drawdown worse than the stock control (C-B)** at **either**
concurrency cap. `max_drawdown` is **NEGATIVE**, so an improvement is `arm − base > 0` — the sign
error `S10` shipped and `U3` pinned, and it is pinned again here by a test carrying a real
measured pair.

---

## 5. Controls (both stages)

* **C1** — the covered-row count, the healthy/unhealthy split and the date list reproduce §1c
  exactly; the run **ABORTS** before any measurement otherwise.
* **C2** — **ZERO** point-in-time violations: no surface row dated `> d` enters any statistic at
  `d`, and no forward path is read before it exists. Counted, not asserted.
* **C3** — `skew_25d` is verified to equal `iv_put_25d − iv_call_25d` to `0.000e+00` on the
  covered rows, so it can never be reported as independent evidence (§1b).
* **C4** — the selected D4 contract's realised delta is within **0.05** of the −0.25 target, and
  its DTE inside [30, 45]. A drifting delta makes D4 a different trade under the same name —
  `O6`'s failure mode, where cheapness rules moved the exposure.
* **C5** — M1 re-measured on the covered rows (§2), reported whatever it says. **If M1's
  separation is absent on the covered subsample, that is reported as the headline**, because the
  entire trade rests on it.
* **C6** — the healthy and unhealthy sets are compared on **market cap, sector and beta**, so an
  IV gap that is really a size or sector gap is visible rather than read as a pricing gap
  (`U7`'s and `S10`'s failure mode).
* **C7** — stage 2 only: the arm's own contract set is checked to be **100% puts**, since this
  lane has now twice confused a book's composition with a cache's.

---

## 6. Expectations, written before any number (scored honestly at the end)

| # | expectation | confidence |
|---|---|---|
| 1 | **D1 shows real elevation** — post-dip `atm_iv_30` is ≥ 20% above the name's own baseline | 85/15 |
| 2 | **G2 FAILS**: the market discriminates, healthy dips carrying visibly cheaper vol | 55/45 |
| 3 | **D6 (VRP) is positive** on the healthy set | 60/40 |
| 4 | **M1's separation on the covered subsample is far smaller than 10.84pp**, per §1d | 80/20 |
| 5 | **The gate CLOSES** (any one of G1–G3 fails) | 55/45 |
| 6 | If stage 2 runs, **it is REJECTED**, A3's result dominating | 70/30 |
| 7 | The decay in D2 is **fast** — most of the elevation gone inside 30 trading days | 65/35 |

**Expectation 2 is the one I most want to be wrong about, which is exactly why it is written
down.** This project's directional calls have been wrong more often than right.

---

## 7. Trial cost

**Stage 1 charges ONE options trial.** It has no arms and returns no verdict about the world, but
it does carry a **pre-committed bar with a decision consequence** (§3), and `O21`'s correction is
explicit that a row with a pre-committed bar and a verdict against it is a trial even when nothing
is adopted. G1–G3 are a **conjunction forming one gate**, not three searches — the same accounting
`U3`'s two-leg A1 used. **Options `N` 287 → 288.**

**Stage 2, if it runs, charges FOUR further options trials** — the healthy arm plus C-A, C-B and
C-C, each of which could independently have been reported as a finding. **288 → 292.** The
mirror (C-D) is an instrument self-test and charges nothing.

**Equity `N` is untouched at 212.** The population is an equity one but the search is over option
pricing, and `N` is domain-scoped. **The premise probe (§1) charges nothing** — `S25`'s precedent:
facts about what data exists are not hypotheses.

**Re-read `by_domain` after merging** rather than quoting these figures from mid-run; other lanes
land concurrently, and this file's own record shows an equity figure misquoted that way twice.

---

## 8. Void conditions

1. Any change to §3's gate, §4.2's bar or §4.4 after any stage-1 or stage-2 number is read.
2. Stage 2 running when the gate did not open, or the gate being re-scored after stage 2.
3. Any arm beyond those named in §4 and §4.1, or any exit/strike/DTE grid being swept.
4. Any change to V6's `QUALITY_FLOOR` or `HEALTH_FLOOR`, or to the dip depth (V6-B's void 6.3).
5. Selecting the exit rule, the delta target or the DTE band on the results.
6. Quoting `X7`'s calibrated floors against any statistic here (§3.1).
7. Quoting a stage-2 result against M1's **−10.84pp** rather than the covered subsample's own
   re-measured separation (§1d, C5).
8. Reporting a clearing stage-2 arm as `ADOPTED` rather than `ELIGIBLE-BUT-UNRESOLVED` (§4.3).
9. Quoting the ρ-adjusted fill as the headline (§4).
10. Reporting `skew_25d` and the put-minus-call spread as two pieces of evidence (§1b, C3).
