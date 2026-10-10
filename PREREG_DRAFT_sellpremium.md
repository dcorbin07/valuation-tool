# PREREG DRAFT — SELL-PREMIUM — selling the expensive premium after a sharp drop

**A DRAFT AND NOT A REGISTER. ZERO TRIALS.** No arm is run, no option is priced, no trial is
booked. A register is committed **ALONE** by the executor (markdown only, zero `.py`, a strict git
ancestor of every measurement commit) — `RESEARCH_CHARTER.md` §3.

**AUTHORISATION, STATED PRECISELY BECAUSE IT IS WIDER THAN THE NAMED INSTANCE.**
`DECISIONS.md` 2026-10-08 is headed *"DEVELOP A PROFITABLE OPTIONS STRATEGY"* and its named
instance is *"calls after a sharp drop"*. **The headline covers the sell side; the named instance
does not.** This draft is the sell side and is relayed under the headline. If Don reads the ruling
narrowly, this draft is a proposal awaiting his word rather than an authorised program — flagged
rather than assumed.

**WHAT IS MEASURED HERE AND WHAT IS NOT.** Three censuses are run below and declared as such:
the options cache's coverage by year (§3), the tier's share prices (§5), and SPY's own worst
rolling returns (§4) — a property of a public benchmark. **No forward option return is priced
anywhere in this draft**, and every return figure quoted is **landed** in `V6OPT_STAGE2.json`,
`DIPCALL2_ARM.json`, `OPTIONS_VRP_RESULTS.md`, `O10_O18_TICKFLOW.json` or
`O11_O19_O22_O25_PORTFOLIO.json`, or is arithmetic on those shown in full. Under `MB1-SEL` a
census can only ever **BLOCK** this program, never produce a finding for it.

---

## 1. IS IT NEW? — YES, AND THE PROMPT'S OWN AXIS IS THE WRONG ONE

The question put to this lane is whether *"sell puts (cash-secured, no margin — a Roth) after a
sharp drop in a $10B name, **conditioned on the drop rather than on health**"* is new or a re-run
of `V6-OPT`. **It is new. And the clause in bold drops the one ingredient the record says makes it
work, for a reason `V6-OPT` measured rather than guessed.**

### 1a. What is a re-run, and it already has an answer

**"Does conditioning on a dip beat not conditioning, for a short put?" IS ANSWERED.** `V6-OPT`'s
`C-C` control is a cash-secured put on **a random day in the same name-year**, five seeds, and the
dip-conditioned arm beat it on a paired name-year sign test at **306 of 457 cells positive
(66.96%), z +7.2506, p 4.15e-13**. Pooled across the five seeds the control earns **+0.2612%** per
trade against the arm's **+1.1342%**. Re-asking that exact question on the same event is a re-run
and this draft does not.

### 1b. What is new — three things, and the first is `V6-OPT`'s own nominated successor

1. **THE STRIKE RULE.** `V6-OPT` closed with the sentence that licenses this register:
   *"A risk signal can only pay through an option if the MONEYNESS is held fixed, not the DELTA —
   and that is a NEW hypothesis needing its own register, forbidden here by void condition 3."*
   A pre-commitment naming its own successor before its own verdict existed is the strongest
   licence available (`SC-1b`'s precedent).
2. **THE EVENT.** `V6`'s dip is a **state** — down ≥20% from a 252-session high — and `CLAUDE.md`
   records it as substantially an inverse-momentum sort (Spearman **+0.6642** against the
   `momentum` theme). `DIP-CALL-2`'s event is an **acute one-day shock**, a return at or below
   −2.5× the name's own trailing 60-session volatility taken `shift(1)`. They are different
   objects and may overlap; neither is the other.
3. **THE DECOMPOSITION IN §2 HAS NEVER BEEN DONE**, and it reorganises the question.

### 1c. WHY "RATHER THAN HEALTH" IS THE WRONG AXIS — the mechanism is measured, not argued

`V6-OPT` was rejected on condition 2: the identical trade on **unhealthy** dips earned **more**
(+1.2651% against +1.1342%) in both halves, so the health filter did nothing. **But the paired
test on that comparison is not significant — 55 of 120 cells positive (45.83%), z −0.9129,
p 0.3613** — so the honest statement is *"health could not be shown to discriminate"*, not
*"health is worthless"*.

**And the reason it could not is measured.** `V6-B` found healthy dips fall a further 20% some
**10.8pp less often** (HAC *t* −10.5847, both halves), re-measured on `V6-OPT`'s own covered rows
at **−2.797pp**. Yet `V6-OPT`'s assignment rates came back **25.303% healthy against 25.727%
unhealthy — a 0.43pp gap.** A real risk difference of 2.8 to 10.8pp was compressed to 0.43pp.
**The strike rule did that: a delta target sets the strike from the name's own volatility, so it
equalises assignment probability by construction and a risk signal has nothing left to move.**

**So at FIXED MONEYNESS the reason health failed is removed.** Dropping health and keeping only
the drop is therefore the **weaker** of the two designs, and this draft keeps health as a
**factorial factor** (`A4`), never as a filter. That is a correction to the brief, made before any
outcome exists.

---

## 2. THE DECOMPOSITION — FREE, ON LANDED NUMBERS, AND IT DECIDES WHAT CAN BE ASKED

A short put is a **long-delta** position. `V6-OPT` banked all three numbers needed to split its
return, and the identity reproduces them:

| quantity | landed value | source |
|---|---|---|
| cash-secured put, healthy dips | **+1.1342%/trade** | `V6OPT_STAGE2.json` `arms/A_healthy_csp/mean` |
| the **stock** on the same dates | **+3.4269%/trade** | `arms/CB_stock/mean` |
| median put delta | **−0.265** | `V6OPT_STAGE1.json` `C4` |

`delta × stock return` = 0.265 × 3.4269 = **+0.9081pp**, leaving a residual of **+0.2261pp**.

> **80.1% OF WHAT A POST-DIP SHORT PUT EARNS IS THE STOCK'S OWN DRIFT, TAKEN AT A QUARTER OF THE
> EXPOSURE. THE OPTION-SPECIFIC PART IS +0.2261pp/trade — ABOUT +2.61%/yr AT 32-DAY TURNS.**

This also explains the ratio nobody had explained: **+3.4269 / +1.1342 = 3.02**, against
1 / 0.265 = 3.77. The stock earns about three times the put because it carries about four times
the delta, and the put makes up the difference out of premium.

**THE CONSEQUENCE FOR DESIGN, AND IT IS THE SAME SHAPE AS `DIP-CALL-3`'s: the thing that makes
this an OPTION trade is 8 to 20 times below what the owned data can detect.** At `V6-OPT`'s own
per-trade SD of **5.047pp** and the options hurdle **derived not quoted** (`N` = 310 →
**3.3872031**; it moves, re-derive it):

| effect to detect | events needed at 80% power |
|---|---|
| +2.0000pp | 114 |
| **+1.1342pp** (`V6-OPT`'s measured total) | **354** |
| +0.8000pp | 711 |
| +0.5000pp | 1,821 |
| **+0.2261pp** (the option-specific residual) | **8,904** |

**ONLY THE BOLD ROWS ARE ON THIS ARM'S OWN SCALE** — a return on secured cash. The others are
round references. **`O7`'s measured richness of −0.6739pp is deliberately NOT in this table**: it
is implied minus realised **move**, a property of the underlying, and feeding it into a
secured-cash power calculation is the category error `V5-REREAD` caught at **~12×** when audit
`B11`'s equity cost in bps of *stock notional* was used as a bar for a book paying bps of
*premium*.

Against §3's priceable bracket of **437 to 1,100**. **So a cash-secured arm can confirm that the
trade pays and cannot say whether any of it is the option.** The register states that before it
runs, and §6 designs around it.

---

## 3. COVERAGE — MEASURED ON THIS ARM'S OWN POPULATION, WHICH IS `O-1`'s LESSON

`O-1` published *"~75% chain coverage"*, measured it at **5.89% of panel cells**, and recorded the
cause: an **alert-book** figure applied to the **panel**, ~17× wrong. Coverage is therefore
measured here on the tier this arm trades, in three layers.

**LAYER 1 — the cache has no year hole, and that corrects an assumption the record invites.** The
EOD chain cache is per ticker-year and `.pkl` files exist for **every year 2016–2025**:

| year | tickers with a chain file | `.missing` | `.oi_degraded` |
|---|---|---|---|
| 2016 | 401 | 64 | **360** |
| 2017 | 408 | 78 | **350** |
| 2018 | 420 | 91 | **353** |
| 2019 | 441 | 4 | 0 |
| **2020** | **454** | 6 | 1 |
| 2021 | 483 | 5 | 2 |
| **2022** | **486** | 5 | 0 |
| 2023 | 494 | 5 | 1 |
| 2024 | 960 | 601 | 1 |
| 2025 | 516 | 3 | 4 |

**The record's repeated "2016–2018 only" is about the Tier E LONG-TENOR pull (200–858 DTE), not
this cache.** `SC-3` measured that restriction and it binds past 200 DTE; **at 20–60 DTE, 2020 and
2022 are priceable.** Verified as population and not existence: `AAPL-2020.pkl` carries **253
dates, 2020-01-02 → 2020-12-31**, and `AAPL-2022.pkl` **251 dates** — every session, the crash
included.

**LAYER 2 — tier names with a file.** On the build quadrant's $10B tier (**459** names, half 0,
from `DIPCALL_CENSUS.json`): **180 / 183 / 187 / 195** names carry a chain file in 2016 / 2017 /
2018 / 2019 — **39.2% to 42.5%**. On the check quadrant's tier (**570** names, half 1): 2020
**38.1%**, 2022 **40.9%**, 2024 **73.5%**, **2026 ZERO**.

**LAYER 3 — and this is the binding one. A file is not a usable put.** Spot-check, 14 random tier
names with both a price series and a chain, 20 sampled sessions each (280 cells):

| funnel step | 2018 | 2020 |
|---|---|---|
| any put row | 280 (1.000) | 280 (1.000) |
| + an expiry at 25–45 DTE | 234 (0.836) | 237 (0.846) |
| + a strike in 0.85–0.95 moneyness | 147 (0.525) | 194 (0.693) |
| **+ a two-sided quote (`bid > 0`, `ask > bid`)** | **48 (0.171)** | **135 (0.482)** |
| the same at **20–60 DTE** | **83 (0.296)** | **190 (0.679)** |

**THE QUOTE IS WHAT BINDS, NOT THE TENOR OR THE STRIKE** — 147 → 48 in 2018, a 67% loss — and
2016–2018 is exactly where the `.oi_degraded` markers sit (`AAPL-2016`: *"coverage 0.771856 floor
0.95"*). `MA45` measured **26.08%** of 4.35M cached rows one-sided; this is that, concentrated in
the early years.

**SO THE TENOR BAND IS 20–60 DTE AND NOT `V6-OPT`'s 30–45, DECLARED NOW AND ON COVERAGE GROUNDS
ALONE.** It nearly doubles 2018's usable cells (0.171 → 0.296). **Widening a band after seeing
returns would be choosing the design on the outcome (`MA58`'s void condition 5); widening it on a
coverage census before any arm runs is the opposite act**, and the reason is recorded here so a
reader can check which happened.

**THE PRICEABLE BRACKET.** `DIPCALL_YEARS.json` banks **6,390** k=2.5 events in 2016–2019 over
**826 distinct event days**. Applying layer 2 (0.40) and layer 3 at 20–60 DTE gives **6,390 × 0.40
× 0.296 ≈ 757**, and at 25–45 DTE **≈ 437**. **`K1` makes measuring it the register's first act,
and the estimate is an estimate.**

**ONE FAVOURABLE SIDE EFFECT OF SPARSE COVERAGE, worth stating because it runs the design's way:
the coverage filter DE-CLUSTERS the event set.** 757 covered events over roughly 380 covered days
is ~2 per day, against 7.06 per day raw, so the design effect shrinks. **It must still be MEASURED
against a shuffled null, because `R3` established that a raw design effect is not evidence of
clustering** — 600 independent draws in 12 blocks returned ~1.8 from sampling error alone.

---

## 4. A3 — THE RECONCILIATION THE PROMPT ASKS FOR, AND IT CORRECTS THE RECORD TWICE

`A3` is the standing corpse: **−7.99%/trade**, 2,496 closed trades from 119,976 candidate days, 55
names, 2016–2025, negative in both halves (−8.31% / −7.70%), in 9 of 10 years, in every IV-rank
band and on 53 of 55 names. It is quoted across the fleet as the thing a premium-selling book must
out-select. **Read against `V6-OPT` it is far less hostile than it reads, and far more hostile in
one specific place.**

### 4a. CORRECTION 1 — `A3` is not what two fleet declarations say it is

`DECL_f10_clean_csp.md` and `DECL_f4_eventfree_premium.md` both describe it as **"alert-day credit
spreads"**. Verified in `A3`'s own runner: `optvrp_run.py` loops over **every trading day** in the
window and gates on **`iv_rank >= 0.50`** against the name's own trailing 252 observations
(`options_vrp.py:211`). **There is no alert-day conditioning.** The `alert_ts` field in its trade
record is a reused column name in the shared record, not a filter. **Reported, not edited** —
`RUN_RULES` rule 3; those are the options-bot lane's files.

### 4b. CORRECTION 2 — the two percentages have never been comparable, and the gap is ~20×

| | **A3** | **V6-OPT** |
|---|---|---|
| structure | put **credit spread**, $5 wide | **naked** cash-secured put |
| strike | 20-delta short leg | 25-delta (median −0.2638) |
| tenor | 25–50 DTE (median 36) | 30–45 DTE (median 32) |
| entry | any day, `iv_rank ≥ 0.50` | a dip date passing health floors |
| exit | +50% target / **2× credit stop** / 21-DTE | **hold to expiry** |
| crossings | **four** (two legs, two ways) | **one** |
| **denominator** | **max risk** = width − credit ≈ **$449** | **the strike** ≈ **$4,411** (§5) |
| result | **−7.99%** | **+1.1342%** |

**A3's denominator is roughly TEN times smaller on the tier's median share price — $449 against
$4,411, a factor of 9.8 — and more on a higher-priced name. So quoting "−7.99% against +1.13%"
overstates `A3`'s severity by about an order of magnitude.** Per share: `A3` loses
**−$0.359** at the touch; `V6-OPT` earns **+$1.045**. `A3`'s own cost accounting explains a
quarter of that gap directly — *"roughly $28 is the bid-ask crossed twice on two legs"*, i.e.
**$0.28/share against `V6-OPT`'s single crossing.**

### 4c. WHAT SURVIVES THE RECONCILIATION AND IS THE REAL HOSTILE FACT

**`A3`'s LEVEL, at a fill nobody can achieve.** At aggression 0.00 — perfect mid on both legs both
ways — it returns **+0.13%, profit factor 1.02**, against a 1.20 bar, **negative in the first
half**, and it still lowers the combined Sharpe 0.87 → 0.77. `A3`'s own sentence:

> *"There is no premium being lost to execution here, because there is no premium."*

**So the gross single-name variance risk premium, net of a $5 wing, on 55 liquid large caps over
ten years, is approximately ZERO.** That is clean, it is not a cost artefact, and it is the
strongest evidence against this program. It also agrees with §2's residual: **+0.2261pp/trade is
+2.61%/yr — small, positive, and below `A3`'s resolution.** Two independent instruments agreeing
that the number is small.

### 4d. WHAT DOES NOT SURVIVE — `A3`'s IV-RANK GRADIENT IS CONFOUNDED TWICE, IN THE SAME DIRECTION

This matters because **"sell premium after a drop" IS "sell premium at high IV rank"** — `V6-OPT`
measured post-dip IV at **+17.711%** above the name's own trailing median — so `A3`'s gradient
looks like a direct refutation:

| IV-rank band | n | expectancy | profit factor |
|---|---|---|---|
| 0.50–0.65 | 877 | **−6.24%** | 0.34 |
| 0.65–0.80 | 648 | **−8.16%** | 0.27 |
| ≥ 0.80 | 971 | **−9.45%** | 0.25 |

**Monotone, and it is read at aggression 1.00 on a structure with two vol-dependent leaks.**
Computed on the tier's median share price ($49.01, §5), 36 DTE, $5 width, 20-delta short:

| IV | spread credit as a share of the naked premium |
|---|---|
| 0.25 | **0.968** |
| 0.35 | 0.906 |
| 0.43 | 0.851 |
| 0.60 | 0.745 |
| 0.80 | **0.648** |

**A FIXED-DOLLAR WING GIVES AWAY A MONOTONICALLY RISING SHARE OF THE GROSS PREMIUM AS IV RISES —
3.2% at IV 0.25, 35.2% at IV 0.80 — and the 2× stop is set on that shrinking credit while the
distribution it must survive is widening.** Add the four crossings, whose absolute cost also rises
with IV. **So `A3`'s gradient is the gradient of a $5-wide stopped spread, and at least two of its
three slopes are structural.** It is **not** clean evidence about a naked put held to expiry.

**THAT IS WHAT `K2` EXISTS TO SETTLE, FOR FREE** — §6.

---

## 5. WHAT A CASH-SECURED PUT ACTUALLY TIES UP, AND THE TWO STRIKE RULES SIDE BY SIDE

**THE DENOMINATOR IS THE STRIKE, NOT THE PREMIUM**, and `V6-OPT` recorded that
`options_sizing` gets this wrong for a short: *"quoting a short on premium overstates it ~40x on
this book."* Census of the 187 build-tier names holding both a price series and a 2018 chain,
median close over 2016–2019:

| percentile | share price | cash per 0.90-strike contract |
|---|---|---|
| p05 | $13.30 | $1,196.70 |
| p25 | $30.77 | $2,768.89 |
| **median** | **$49.01** | **$4,410.77** |
| p75 | $82.57 | $7,431.64 |
| p95 | $160.64 | $14,457.58 |
| max | $283.03 | $25,472.38 |

**A cap-10 equal-secured book needs about $44,100 at the median name and $144,576 at the p95
name.** So **`MB3`'s affordability wall binds on the tail, not the median** — a measurement that
ran in the design's favour against my own assumption, and `K4` makes the skip reason a recorded
field (`MB3`: *"the low-end failures are AFFORDABILITY, not ruin — the book never gets on"*).

**AND HERE IS WHAT THE TWO STRIKE RULES ACTUALLY DO.** Black-Scholes, 32 days, r = 0, S = 1:

| IV | **0.90 moneyness**: put delta | premium/strike | annualised | **25 delta**: moneyness | premium/strike |
|---|---|---|---|---|---|
| 0.25 | −0.0721 | 0.272% | 3.14% | 0.9539 | 1.202% |
| 0.30 | −0.1092 | 0.540% | 6.34% | 0.9456 | 1.466% |
| 0.35 | −0.1426 | 0.881% | 10.52% | 0.9375 | 1.738% |
| **0.43** | **−0.1864** | **1.535%** | **18.97%** | **0.9252** | **2.191%** |
| 0.50 | −0.2160 | 2.183% | 27.92% | 0.9149 | 2.605% |
| 0.60 | −0.2477 | 3.188% | 43.04% | 0.9012 | 3.224% |
| 0.80 | −0.2866 | 5.359% | 81.38% | 0.8766 | 4.564% |

**THE CHECK AGAINST THE REAL TRADE, AND IT MISSES — IN THE CONSERVATIVE DIRECTION.** At IV 0.430,
`V6-OPT`'s own measured post-dip level, the table puts a 25-delta put at **2.191% of strike**
against the **2.550%** `V6-OPT` actually collected **net of a full touch crossing** — so the
arithmetic lands **14% BELOW** a figure that should sit below it, not above. **Hypothesis, not a
measurement: a 25-delta put trades above ATM implied vol, and 0.430 is the ATM 30-day level**, so
the table omits the put skew. **The direction is the safe one** — it understates a seller's income
throughout, including in §6's `K3` crash table — and it is stated rather than tidied because an
arithmetic check that misses by 14% is not a reproduction.

> **HOLDING MONEYNESS FIXED IS NOT A RISK-DISCRIMINATION RULE. IT IS A VOL-TIMING SIZING RULE:
> 0.27% of strike at IV 0.25 and 5.36% at IV 0.80, a twenty-fold range, with delta rising 0.07 →
> 0.29 alongside.** It sells more premium exactly where vol is highest — which is exactly the act
> `A3`'s gradient appears to condemn and §4d shows it does not cleanly condemn. **The whole
> register turns on that one question**, and `K2` answers it before any arm runs.

---

## 6. THE FREE PRE-OUTCOME KILLS — ZERO TRIALS, READ IN THEIR OWN PASS BEFORE ANY ARM

Each runs in a **separate pass** and the arm runner **refuses** without a passing artifact —
`O10`'s process defect (*"C2 and the outcome statistics were computed in the SAME pass, so it
cannot be claimed the control was read before the numbers"*), not repeated. `MB1-SEL`: a control
can only BLOCK.

**`K1` — COVERAGE, on this arm's own population.** Floors, fixed here: **≥ 400 priceable events**
and **≥ 150 distinct covered event days** in the build quadrant at 20–60 DTE and 0.85–0.95
moneyness with a two-sided quote. §3 estimates 757 and ~380; if the measurement lands below
either floor the register **STOPS and the arm never runs** — `W-28`'s outcome, and `W-28`'s rule
forbids relaxing a floor after watching it fail.

**`K2` — THE PREMISE: RE-PRICE `A3`'s OWN TRADES AS NAKED PUTS HELD TO EXPIRY, AT THE MID, BY
IV-RANK BAND.** `A3` banked 2,496 trades with both legs; re-pricing the short leg alone, with no
stop and no wing, costs nothing new. **Restricted to `A3`'s 2016–2019 subsample**, so no
check-quadrant year is read. This is `DC-1`'s shape — a kill that tests the register's **PREMISE**
rather than its hypothesis — and `DC-1` booked **zero trials** for exactly that.
* **If the IV-rank gradient PERSISTS on a naked, unstopped, mid-filled structure, the moneyness
  arm is WITHDRAWN before it runs** and the program's central mechanism is dead for free.
* **If it FLATTENS, `A3`'s gradient was structure and cost**, and §4d's confound is confirmed
  rather than argued.
* **Either way it is a finding**, which is what makes it worth running first. Stated in advance:
  this is the single most likely place this program dies.

**`K3` — THE MECHANICAL CRASH STRESS.** Public-index arithmetic, no quadrant look: a 0.90-moneyness
cash-secured put loses `(x − 0.10) / 0.90` of secured cash when the name falls `x` over the tenor.
SPY's own worst 32-session return by year, measured from the shipped `SPY.csv`:

| episode | fall | loss on secured cash | net of 1.13% premium | years of premium |
|---|---|---|---|---|
| **2018** — the worst in the Stage-1 window | −14.31% | −4.79% | −3.65% | **0.28** |
| 2022 | −16.53% | −7.26% | −6.12% | 0.47 |
| 2025 | −17.32% | −8.13% | −7.00% | 0.54 |
| **2020** | **−32.61%** | **−25.12%** | **−23.99%** | **1.85** |
| 2008 | −32.74% | −25.27% | −24.13% | 1.87 |
| a single name at 1.4× the index in 2020 | −45.65% | −39.61% | −38.48% | **2.97** |

**THE CRASH DOES NOT FORECLOSE THIS PROGRAM, AND THAT IS THE SHARPEST CONTRAST WITH `DIP-CALL`.**
Buying calls after a drop was killed by arithmetic no data could change (the drift is 5.6–9.3% of
the implied move). Here one crash month costs **1.85 to 2.97 years** of premium — painful, finite,
and recoverable from premium alone. **`K3` kills only if the register's measured strike
distribution makes the figure worse than 6 years**, fixed here before it is computed.

**AND THE SHAPE OF THE RISK IS THE OPPOSITE OF `O11`'s.** `O11` found *"the edge lives in the
crowded weeks and a concurrency cap refuses exactly those"* — expectancy −4.51% in quiet weeks
against +14.28% above the 90th percentile, 1,677 of 3,870 trades refused at cap 10. **For a SHORT
book the inversion is protective: the RISK lives in the crowded weeks** (at k=2.5 the worst ten
days carry **14.05%** of all events) **and the cap refuses exactly those.** The cap bounds the
crash loss at roughly one book-width however many events fire. Stated as a mechanism, not a
result.

**`K4` — AFFORDABILITY.** §5's census, re-measured on the arm's own events, with the **skip reason
recorded as a field** so an affordability skip is never counted as a concurrency skip (`MB3`).

---

## 7. THE ARMS — 5 OPTIONS TRIALS, BH AT q = 0.10 ACROSS k = 5

Membership fixed here, before any arm runs (charter §5: *"choosing afterwards which arms were in
the batch is how BH is gamed"*). Thresholds **0.02 / 0.04 / 0.06 / 0.08 / 0.10**. **Every critical
value LABELLED UNCALIBRATED** — `V2G` and `R1-VAR`: no calibrated floor exists for a paired
within-panel difference, and `UNIVERSE-BIAS` part 2 means no X7 floor transfers to this universe.

**EVENT, identical to `DIP-CALL-2`'s and not re-chosen:** a daily return ≤ **−2.5×** the name's own
trailing 60-session return volatility, `shift(1)`, on the **point-in-time** $10B tier at the event
date — **never ever-in-tier**, which would be survival selection. Build quadrant, options-era
intersection: **2016–2019 × ticker half 0.** **The price basis for the EVENT is the adjusted
series** (`V6`'s `C5`: on a raw series a 2-for-1 split reads as −50%, and companies split *after*
they rise). **The price basis for the STRIKE and for settlement is the AS-TRADED series**
(`O-1`'s MNST 3-for-1 booked a fake +1453%). Both, in one register, in opposite places.

**`A1` — THE MECHANISM, AND THE ONLY ARM WITH POWER ON THE OPTION-SPECIFIC QUESTION.** A
**daily-delta-hedged** short 0.90-moneyness put, 20–60 DTE, on the event, against the same
structure on a random day in the same name-year. **This is `O3`/`O4`/`O5`'s instrument and its
power argument is the reason**: that register measured delta-hedged dispersion at **sd 0.0303
against the straddle's 0.9055, a 30-fold reduction**, and recorded *"the power argument held,
which is the only reason the trials were worth spending."* **DECLARED: this arm is NOT TRADEABLE
IN A ROTH** — it requires shorting the underlying — so it can never be a product and exists only
to say whether there is anything in the premium at all. `O3`/`O4`/`O5` separately measured the
mean delta-hedged gain to a **buyer** at **−0.0072 with every quintile of every arm negative**,
i.e. a positive premium to the **seller**, reproduced without being targeted; this arm asks
whether the drop raises it.

**`A2` — THE PRODUCT, AND ITS COMPARATOR IS THE STOCK, NOT ZERO.** A cash-secured 0.90-moneyness
put, 20–60 DTE, held to expiry, **net of a full touch crossing at entry** (`V6-OPT`'s convention).
**A SHORT PUT HELD TO EXPIRY CROSSES ONCE**, not twice: `MA46` established that *"an expiring
option is never SOLD, so there is no second commission leg"*, and the same holds for the spread —
which is the structural reason the sell side's cost arithmetic is better than `DIP-CALL`'s
round-trip. **`O18`'s ρ = 0.6743 is NOT used as a discount, and the reason is that it carries no
verdict:** `O10_O18_TICKFLOW.json` records `c2_gate.separation_holds = false` and stamps the
registered-primary blocks **VOID** — *"only the all-codes arm is reported, WITH NO VERDICT for
either item"* — and its own artifact discloses that the gate and the outcome statistics were
computed in the same pass. **So the touch is charged in full and ρ is cited only as a reason the
charge is conservative, never as a number subtracted from it.** **PRE-COMMITTED: beating zero is
NOT a pass.** §2
shows 80.1% of this arm's return is delta × drift, so a zero bar would confirm the equity drift
through an option wrapper and call it an options strategy. **The bar is the paired difference
against holding the stock on the same dates**, and §8 fixes what that bar may be.

**`A3'` — THE STRIKE RULE.** The **paired** difference, moneyness − delta, on the **identical**
events. **No standard error is borrowed** (`MB8`: a paired difference between two highly
correlated books is measured far more precisely, and an se may not travel across perturbation
sizes); the register measures its own and reports its own MDE beside the verdict (`MB22`: the
80%-power figure is `(crit + 0.84) · se`, and every MDE this project published before `MB22` was a
50%-power figure).

**`A4` — HEALTH, AS A FACTOR AND NOT A FILTER.** The paired healthy − unhealthy difference **at
fixed moneyness**. §1c is the hypothesis: the 0.43pp assignment gap was the strike rule's doing,
so at fixed moneyness a real 2.8pp risk difference should reappear. **`V6-OPT`'s health floors are
IMPORTED and never re-implemented** (`B7`), and **re-tuning them is a void condition** —
`V6-OPT`'s own §6.3.

**`A5` — IS IT THE DIP, OR JUST SHORT VOL?** The cash-secured arm against a random-day
cash-secured put in the same name-year, **five seeds minimum** (the standing rule: a single seed
flipped `R2`'s verdict), verdict on the **paired name-year sign test**, which is the statistic
`R2` and `V6-OPT` both rest on. **This is the arm that separates the program from `A3`'s corpse**,
and `A3`'s own entry gate (`iv_rank ≥ 0.50`, any day) is the nearest thing to the control.

---

## 8. SURVIVABILITY, AND DON'S STANDING RULING, WHICH BINDS BEFORE ANY ARM RUNS

**`O11` GOVERNS: positive per-trade expectancy is not survivability.** It measured a book at
**+3.27%/trade** ending at **$37,059 from $50,000** at cap 10 — three of four cells UNSURVIVABLE,
the fourth MARGINAL, none SURVIVABLE. The grid here is **$25k / $50k / $100k / $250k × cap 10 /
50**, with the affordability skip and the concurrency skip recorded as **separate** fields.

**AND THE DRAWDOWN MUST BE CAPITAL-WEIGHTED, BECAUSE THE PUT'S ONLY MEASURED ADVANTAGE RESTS ON A
CONSTRUCTION ITS OWN ARTIFACT DISCLAIMS.** `V6OPT_STAGE2.json` reports cap-10 max drawdown
**−55.52%** for the put against **−82.56%** for the stock, and then says of its own method:

> *"max_drawdown here compounds the per-trade returns SEQUENTIALLY in entry order. It is NOT a
> capital-weighted portfolio equity curve … so it OVERSTATES drawdown."*

**So the one thing the short put has going for it has never been measured on a proper book.** That
gap is real and it is this register's most defensible contribution.

**`R1-VAR` IS DON'S STANDING RULING AND IT IS THE BAR `A2` MUST CLEAR:**

> *"A SHARPE OR VOLATILITY GAIN BOUGHT WITH ALPHA IS NOT WORTH HAVING UNLESS THE SHARPE ITSELF IS
> BAD."*

The book runs **Sharpe 0.5866** at an IR of **~0.88/yr** vs SPY, so the antecedent does not fire.
**`V6-OPT` measured the put giving up 2.29pp/trade of return against the stock** (+1.1342 vs
+3.4269) **to cut drawdown** — which is precisely a risk gain bought with return, and Don has
already declined that trade once. **Therefore `A2`'s non-inferiority margin on return must be a
number Don would actually adopt, and `R1-VAR`'s own lesson forbids borrowing a detection threshold
to serve as a preference threshold** (*"X7's alpha margin is a DETECTION threshold and was used as
a PREFERENCE threshold… the two have no reason to coincide"*). **The margin is Don's to set and is
left BLANK in this draft rather than invented.** A register committed with that field blank is
incomplete, by design.

**AND THE DRAWDOWN LEG CANNOT CARRY A VERDICT IN ANY CASE.** `RISK_PRIMARY_MAP.md`'s verdict 3,
re-confirmed by `R1-VAR`: *"drawdown is n = 1 on one COVID quarter."* It is reported as a
**measurement with no verdict**, never as a pass.

---

## 9. THE CRASH IS A STAGE-2 OBLIGATION, AND THE ASYMMETRY IS STRICTER THAN `V6-OPT`'s

The build quadrant's options era is **2016–2019**, whose worst 32-session index move is **−14.31%**
(2018). **The two crashes are in the check quadrant's years** — 2020 at −32.61% and 2022 at
−16.53% — and §3 measured that the cache covers them. So:

* **Stage 1 contains ONE ~14% episode and NO 30% crash.** `V6-OPT` had **one** crash and
  pre-committed, verbatim:

  > *"A decisive REJECT is therefore available … while a decisive ADOPT is not, because a
  > short-vol book's whole risk is concentrated in crash quarters and this sample contains one. A
  > clearing arm is recorded `ELIGIBLE-BUT-UNRESOLVED`, never `ADOPTED` … Nobody may read a
  > rejection here as evidence that cash-secured puts do not work."*

  **That clause is inherited and tightened: Stage 1 here has ZERO 30% crashes, so a Stage-1 pass
  is recorded `ELIGIBLE-BUT-UNRESOLVED` and may not be quoted without that label.**
* **The crash question is answered at Stage 2 and nowhere earlier** — one read of 2020–2026 ×
  half 1, which contains both episodes. That is charter §5 as written, and it means **the one
  thing that can kill this strategy is the one thing Stage 1 cannot see.** Said in advance.
* **Stage 3's forward book is BLOCKED and the blocker is named.** `DECISIONS.md` 2026-10-08:
  Tradier is closed and will not be funded again; Robinhood cannot be used. **And the chain cache
  carries ZERO files for 2026.** So a forward short-put book has neither a broker route nor a data
  route today. `S3-I3` (assignment) is built and `S3-I1` (the fleet harness) refuses every short
  book without it, so the machinery exists and the route does not.

---

## 10. VOID CONDITIONS, EXPECTATIONS, AND WHAT THIS DRAFT DOES NOT SAY

**VOID CONDITIONS.** (1) No grid: one moneyness (0.90), one tenor band (20–60 DTE), one `k` (2.5),
all fixed above. (2) `V6-OPT`'s health floors may not be re-tuned. (3) Quoting `A1` as a product
result — it is not tradeable in a Roth. (4) Quoting `A2` against a zero bar. (5) Quoting any
Stage-1 result without the `ELIGIBLE-BUT-UNRESOLVED` label. (6) Quoting `A3`'s **−7.99%** against
`V6-OPT`'s **+1.1342%** as commensurable — §4b. (7) Re-reading `K2` on `A3`'s 2020–2025
subsample. (8) Reading a drawdown comparison as a verdict (§8).

**EXPECTATIONS, priced now so they can be scored.**
1. **`K2`'s gradient FLATTENS at the mid on a naked structure: 55/45.** The structural confound in
   §4d is measured and monotone; whether it accounts for all three slopes is not.
2. **`A2` clears zero and fails the stock comparison: 70/30.** `V6-OPT` already measured both, on
   a different event.
3. **`A4` finds health discriminating at fixed moneyness: 40/60 against.** The mechanism is
   measured but `V6-OPT`'s paired test on health was p 0.3613, so the effect may simply be small.
4. **`A1` finds a positive post-drop premium to the seller: 60/40**, and finds it **no larger**
   than on a random day: 55/45. If both land, the drop adds nothing and the program reduces to
   `A3`'s question.
5. **`K1` clears its 400-event floor: 65/35.**
6. **My prior that the whole program is adopted: 10%.** The chain that has to hold is long and
   §8's ruling sits at the end of it.

**WHAT THIS DRAFT DOES NOT SAY.** It is **not** a finding that selling premium after a drop works —
no arm has run. It does **not** reopen `V6-OPT`, whose rejection stands on its own pre-committed
condition 2. It does **not** weaken `A3`: §4d narrows what `A3`'s *gradient* can be read to mean
and leaves its *level* — *"there is no premium"* at perfect fills — completely intact, and that
level is the strongest fact against this program. It makes **no claim about index options**, where
the variance risk premium is a different and much better-documented object. And it does **not**
propose a trade: `O11` binds, nothing here licenses real money, and **adoption is Don's and is a
vintage event.**

**NOT DONE, named so it is not mistaken for done:** no register committed, no arm run, no option
priced, no trial booked, no check-quadrant year read at the name level, and `A2`'s non-inferiority
margin left **blank** for Don. `scripts/dipcall_census.py` supplies the event census unchanged;
nothing in this draft edits another lane's files, and §4a is **reported** rather than fixed.
