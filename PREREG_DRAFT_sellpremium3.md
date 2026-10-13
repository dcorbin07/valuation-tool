# PREREG DRAFT — SELL-PREMIUM-3 — the same entries, deployable at a real account size

**A DRAFT AND NOT A REGISTER. ZERO TRIALS.** No arm is run, no option is priced, no trial is
booked. A register is committed **ALONE** by the executor (markdown only, zero `.py`, a strict git
ancestor of every measurement commit) — `RESEARCH_CHARTER.md` §3.

**EVERY NUMBER IS LANDED OR IS ARITHMETIC ON LANDED NUMBERS, SHOWN IN FULL.** Sources:
`SELLPREMIUM2_ARM.json` / `SELLPREMIUM2_KILLS.json` and `HANDOFF_optionsbot.md` §84 for the
measured book; `SELLPREMIUM2_PICKS25.pkl` and `SELLPREMIUM2_BOOK.pkl` for the distributional
anchors below, read as **aggregates only**. **No per-trade spread P&L is computed anywhere in this
draft** — that is the arm, and it is the register's to run.

**THE ANSWER TO THE PROMPT'S CONDITIONAL, UP FRONT: A LONG-LEG RULE DOES SURVIVE, AND THE NARROWEST
ONE DOES NOT.** At a width of **2.5% of spot the spread is NEGATIVE before the assignment cost is
even added** — two crossings plus the long leg's decay exceed the credit — which is `A3`'s death
reproduced on this book's own numbers. From **5% to 12.5%** of spot it survives, and the arm below
declares **one** width.

---

## 1. THE PROBLEM IS NOT THE TRADE, IT IS THE DENOMINATOR

`SELL-PREMIUM-2` passed every clause of `DECISIONS.md` 2026-10-12 — **+0.6709%/trade on secured
cash** (date-clustered *t* +6.375), both halves, **87.47% wins**, a random-day twin beaten at
**z +9.9485** on 657 name-year cells, all eight `O11` cells surviving, and `K3` clearing at
**4.6747 years** against an unrelaxed 6.0. **And at $25k it skips 2,060 of 2,610 trades** because
one contract secures more than $2,500, so it earns **+1.20%/yr**.

**THE WHOLE OF THE FIX IS THE CAPITAL PER TRADE, AND IT IS A RATIO OF 14.** On the landed medians —
spot **$70.55**, moneyness **0.9444** — a naked contract ties up **$6,662.74**. A 7.5%-wide spread
ties up **$469.06**. Nothing about the entry, the short leg or the tenor changes.

---

## 2. WHAT IS UNCHANGED, AND IT IS EVERYTHING EXCEPT THE SECOND LEG

* **THE EVENT** is `DIP-CALL-2`'s, verbatim and not re-chosen: a daily return at or below **−2.5×**
  the name's own trailing 60-session return volatility taken `shift(1)`, on the **point-in-time**
  $10B tier at the event date, never ever-in-tier. **2,610 priceable events over 620 covered days**,
  **398 names**, 2016–2019 × ticker half 0.
* **THE SHORT LEG** is `SELL-PREMIUM-2`'s: the put nearest **25 delta**, solved on the put leg,
  **no moneyness band** (`T3` measured that inheriting 0.85–0.95 would delete **37.47%** of the
  picks, systematically the closest-to-the-money ones).
* **THE TENOR** is **20–60 DTE**, median **37**, `turns_per_year` **6.8108** = 252/37.
* **THE EXIT** is **hold to expiry, no management.** This is load-bearing and §4 is why.
* **THE PRICE BASES** are unchanged in both directions: the **EVENT** on the adjusted series
  (`V6`'s `C5`), the **STRIKES, moneyness and settlement** on the as-traded (`O-1`'s MNST +1453%).
* **THE RAW CHAIN LAYER ONLY** — `options_derived` is two-sided on **1.0000** of its rows **by
  construction**, so any quote funnel measured there reads 1.000 having checked nothing (`MB21`'s
  `C1`).

---

## 3. THE LONG-LEG RULE, CHOSEN BEFORE ANY OUTCOME AND ON A HARD CONSTRAINT

**THE MEASURED ANCHORS, all read off the banked book as aggregates, all as a fraction of the
strike.** The identity that licenses them reproduces §84's headline exactly:

| quantity | value |
|---|---|
| net premium received at the touch, `mean(bid/K)` | **0.015232** |
| expected assignment payoff, `mean(bid/K) − mean(ret)` | **0.008523** |
| market mid = the risk-neutral expected payoff, `mean(mid/K)` | **0.017358** |
| half-spread, `mean((ask−bid)/2/K)` | **0.002127** |
| **check: 0.015232 − 0.008523 =** | **0.006709 = §84's +0.6709%** |

> **AND THE RATIO OF THE SECOND TO THE THIRD IS THE NUMBER THE WHOLE DESIGN TURNS ON:
> 0.008523 / 0.017358 = 0.4910. THE PHYSICAL COST OF THE PROTECTION IS 49.1% OF WHAT THE MARKET
> CHARGES FOR IT — the market charges 2.04×. That is this book's own variance risk premium,
> measured, and it is why the short leg pays.**
>
> **IT IS ALSO EXACTLY WHY THE LONG LEG COSTS.** Buying a long put priced `P` at mid has expected
> value `0.4910·P − P − halfspread = −0.5090·P − halfspread`. **The long leg loses 50.90% of its
> own mid price plus a half-spread, in expectation, on this book's own measured VRP.** Everything
> below is that number fighting the capital reduction.

**THE ARITHMETIC, at the landed medians (spot $70.55, iv 0.2949, 37 DTE), with the assignment-band
equity round trip of §4 included:**

| width (of spot) | K_long | capital | credit net | **E[ret]/trade** | **E[ret]/yr** | crash, years of premium |
|---|---|---|---|---|---|---|
| **2.5%** | $64.86 | $162 | 0.002133 | **−1.37% before the equity cost** | **NEGATIVE** | 1.68 |
| **5.0%** | $63.10 | $310 | 0.006394 | **+2.66%** | **+18.11%** | 1.07 |
| **7.5%** | $61.34 | **$469** | 0.009015 | **+3.38%** | **+22.99%** | **1.15** |
| 10.0% | $59.57 | $636 | 0.010490 | +3.14% | +21.40% | 1.34 |
| 12.5% | $57.80 | $807 | 0.011740 | +2.73% | +18.57% | 1.58 |
| 15.0% | $56.04 | $981 | 0.011583 | +2.33% | +15.89% | 1.87 |
| *naked, MEASURED* | — | *$6,663* | *0.015232* | ***+0.6709%*** | ***+4.569%*** | ***4.6747*** |

**THE RULE: the nearest listed strike at or below `K_short − 0.075 × spot`, REFUSED if the realised
width falls outside [5%, 12.5%] of spot.** One width. No grid.

**AND THE JUSTIFICATION IS A CONSTRAINT FIRST AND A CHOICE SECOND, WHICH IS THE ORDER THAT MATTERS.**
The **5% floor is forced**: below it the credit does not cover two crossings plus the long leg's
decay, and 2.5% is **negative** — that is arithmetic, not preference. The **12.5% ceiling is
forced** the other way: beyond it the capital rises faster than the credit and the return falls
monotonically. **Inside the band the forecast is flat — 18.1% to 23.0%/yr across a 2.5-fold range
of width — so the choice of 7.5% is not fine-tuned, and picking the exact peak would be.** 7.5% is
the midpoint of the admissible band and on the median $70.55 name it maps to the **$5.00 strike
ladder** (7.09%), which is the increment actually listed there.

**A FIXED DOLLAR WIDTH IS REFUSED BY NAME, and the reason is measured: spot runs p05 $22.80 to p95
$237.83, a ten-fold range.** A $5 width is **21.9%** of the p05 name and **2.1%** of the p95 name —
and 2.1% is inside the negative region. **A dollar width would be a different strategy at each end
of the universe.**

**THREE FORECAST HONESTIES, ALL RUNNING THE SAME WAY.** (a) Black-Scholes at the median iv returns
a short-put mid of **$1.0689** against the measured median **$1.0250** and an income of 9.90%/yr
against the measured **9.0811%** — **the model is 4% to 9% optimistic.** (b) The long leg is priced
at the **short leg's** iv, ignoring put skew, so its true cost is **higher** than shown. (c) The
long leg's physical payoff is scaled by the short leg's measured 0.4910 haircut, and a deeper-OTM
strike's physical tail is thinner still relative to its price, so its protection is **overstated**.
**All three flatter the spread.** `K3` and every return are therefore to be computed by the register
on its **own measured net credit at its own strike rule** and never from this table.

---

## 4. THE COSTS A SECOND LEG ADDS — AND IT IS TWO CROSSINGS, NOT FOUR

**THE PROMPT ASKS ABOUT "two crossings in, two out unless left to expire", AND THE EXIT RULE IS
WHAT DECIDES IT.** Held to expiry:

| outcome | frequency (forecast) | crossings |
|---|---|---|
| both legs expire worthless (`S > K_short`) | ~84% | **2** — the entry only |
| short assigned, long worthless (`K_long < S < K_short`) | **11.89%** | 2 + **an equity round trip** |
| both exercise (`S < K_long`) | ~4% | **2** — it settles automatically at the width |

**SO THE OPTION-CROSSING COST IS ONE EXTRA HALF-SPREAD OVER THE NAKED BOOK, NOT THREE.** `A3` paid
four because it **managed exits** — +50% target, 2× credit stop, 21-DTE exit — and its own record
measured what that cost: the hit rate fell **73.7% → 56.4%** as fills worsened, *"converting
winners into stops."* **`SELL-PREMIUM-3` inherits hold-to-expiry precisely so that it does not.**

**AND THERE IS A COST THE PROMPT'S LIST DOES NOT NAME, WHICH I DID NOT EXPECT TO MATTER AND IT
DOES.** In the middle band you are assigned the shares and the long put expires worthless, so you
must **sell the shares** — an equity round trip at this project's own **measured 33.4 bps one way**
(`B11`), on the **short-strike notional**, which is **14.2× the capital at risk**. At 7.5% width:

**0.1189 × 2 × 0.00334 × 14.2 = 1.13% of capital per trade — 25% of the pre-cost edge**, and it is
in the table above. At 5% width it is **1.29%, a third of the edge.** **This is the cost that
makes the narrow widths fail**, and it rises as the width narrows because the middle band widens
relative to the capital.

**Exercising the long put instead would avoid it and is REFUSED by name:** it locks the full width
loss even when `S > K_long`, which is strictly worse than selling the shares.

---

## 5. THE CRASH BAR, RESTATED FOR A CAPPED LOSS — AND THE RESTATEMENT IS THE MOST IMPORTANT SECTION

**WHAT `K3` MEASURED AND WHY IT NO LONGER MEANS THE SAME THING.** `K3` is `loss ÷ annual income`,
in years. For a naked put the loss is `1 − (1−x)/m` of secured cash — **42.49%** on the synthetic
45.68% single-name row — **and you end the crash owning a good company at a discount.** For a
spread the loss is **100% of capital, permanent, and you own nothing.**

**Per position the spread looks far better: 1.15 years against the naked's 4.6747 and a bar of
6.0.** **That reading is correct and it is the wrong frame**, for a reason that is the whole point
of the design:

> **THE SPREAD EXISTS TO DEPLOY MORE POSITIONS, AND THE LOSS IS CAPPED PER POSITION WHILE THE
> NUMBER OF POSITIONS RISES BY THE SAME FACTOR. A 14× SMALLER LOSS PER POSITION ACROSS 14× AS MANY
> POSITIONS IS THE SAME LOSS — AND BECAUSE THE SPREAD'S CAP IS 100% RATHER THAN 42%, IT IS WORSE.**

In a market-wide 32.6% month (SPY's 2020) essentially every 7.5%-OTM long strike is through, so
**every open spread pays its maximum.** The account-level crash cost is therefore **exactly the
deployed fraction of the account**, and nothing in the per-position figure constrains it.

**SO THE BAR MOVES FROM THE POSITION TO THE ACCOUNT, AND IT TIGHTENS RATHER THAN RELAXES.** Three
clauses, all pre-committed here:

1. **`K3-POS` IS RETAINED UNCHANGED AT 6.0 YEARS, with the synthetic single-name row retained** —
   the predecessor's two constraints, untouched. Forecast 1.15.
2. **`K3-ACCT` IS NEW AND IT IS THE GOVERNING LEG: the account-level loss in a 32.6% month may not
   exceed 35% of the account.** 35% is **not chosen** — it is what `SELL-PREMIUM-2` already risks
   at $25k, measured: capital-limited to **3 concurrent naked positions** at $6,662.74, i.e.
   **$19,988 or 80% of the account deployed**, losing **42.49%** of it = **34.0%**. **So the
   successor is held to the incumbent's own account-level crash exposure and may not exceed it.**
   A bar inherited from a measured incumbent is the one kind that cannot be tuned.
3. **THE DEPLOYMENT CAP IS THE DIAL AND IT IS DECLARED, NOT DISCOVERED: a maximum of 35% of account
   equity at risk across all open spreads**, enforced at order time, with the refusal recorded as
   its own reason (`MB3`: affordability is never read as ruin). **`O11`'s concurrency cap stays at
   10 and 50 as a second, independent limit** — whichever binds first.

**WHAT THIS COSTS, SAID PLAINLY: the deployment cap is what converts the forecast +22.99%/yr on
deployed capital into single digits on the account, and it is the price of not risking everything.**

---

## 6. THE ACCOUNT-SIZE TABLE — A REPORTED LEG, NOT A FOOTNOTE

Forecast at 7.5% width: **$469.06 capital per contract, +22.99%/yr on deployed capital.** The
event rate is a hard second ceiling: **2,610 events over 4 years = 652/yr**, and a position
occupies 37/252 of a year, so **the events cannot fill more than 96 concurrent positions at any
capital.**

| account | deployment | positions | deployed | % of account | **forecast %/yr on the account** | **crash cost** | binds on |
|---|---|---|---|---|---|---|---|
| **$10,000** | 35% cap | 7 | $3,283 | 32.8% | **+7.55%** | 32.8% | capital |
| $10,000 | 100% | 21 | $9,850 | 98.5% | +22.65% | **98.5%** | capital |
| **$25,000** | 35% cap | 18 | $8,443 | 33.8% | **+7.76%** | 33.8% | capital |
| $25,000 | 100% | 53 | $24,860 | 99.4% | +22.86% | **99.4%** | capital |
| **$50,000** | 35% cap | 37 | $17,355 | 34.7% | **+7.98%** | 34.7% | capital |
| $50,000 | 100% | 95 | $44,561 | 89.1% | +20.49% | 89.1% | **EVENT RATE** |
| *naked, MEASURED at $25k/cap 10* | *—* | *3* | *$19,988* | *80.0%* | ***+1.20%*** | ***34.0%*** | *affordability* |

**THE COMPARISON THE WHOLE DRAFT EXISTS TO MAKE, AT MATCHED ACCOUNT-LEVEL CRASH EXPOSURE: +7.76%/yr
against +1.20%/yr at $25k, both risking about a third of the account in a 2020-style month — a
6.5× improvement with the crash cost held flat.** That is the claim, and it is a **forecast**: the
register measures it or it is nothing.

**THE 100% ROWS ARE SHOWN TO BE REFUSED, NOT OFFERED.** They are what the strategy does without
clause 3 of §5, and the honest sentence is that a fully-deployed spread book **loses the entire
account** in a 2020 month. They are in the table so nobody discovers them later.

---

## 7. DOES THE TWIN CONTROL STILL MEAN THE SAME THING? — PARTLY, AND THE PART THAT CHANGES MATTERS

Don's clause (b) requires the strategy to beat **the same trade placed on random days in the same
names**. **The twin must become a SPREAD twin at the identical width rule** — a naked twin would
make the comparison *spread-versus-naked* instead of *dip-timing-versus-random-timing*, and the
two differ by the 14× leverage.

**WHAT CARRIES OVER INTACT:** the paired **name-year** unit, the **five-seed** floor (`R2`: one
seed flipped that verdict), and the sign test as the verdict statistic. `SELL-PREMIUM-2` measured
the dip timing at **+0.3317%/trade of strike, 456 of 657 cells positive, z +9.9485** — this is the
arm that separates the family from `A3`'s corpse and it is not re-litigated.

**WHAT CHANGES, AND IT IS A REAL DESIGN PROBLEM: THE DENOMINATOR IS NO LONGER COMMON ACROSS
TRADES.** Secured cash was `K_short × 100` — one number per trade. Spread capital is
`(width − credit) × 100`, and the width is **7.5% of spot** while the credit varies with iv, so
**two trades in the same name-year can have materially different capital.** A mean of
return-on-capital then silently weights the cheapest spreads most. **Pre-committed: the paired
statistic is computed on DOLLARS of P&L per trade, with return-on-capital reported beside it**, and
the per-cell capital dispersion is a required field.

**AND ONE THING THE TWIN CAN NO LONGER DO, STATED BECAUSE IT WEAKENS THE CONTROL.** On the naked
book the twin and the arm tie up identical capital per trade, so a dollar comparison and a
return comparison agree. Here they can disagree, and **if they do, the register reports both and
claims neither** — `MB1`'s lesson, where a median and a mean on one object answered different
questions and only one had been registered.

---

## 8. THE EXTERNAL FACT THAT MUST BE CHECKED AND IS NOT ASSUMED HERE

> **WHETHER A ROTH IRA CAN HOLD A DEFINED-RISK PUT CREDIT SPREAD AT ALL IS A BROKER-POLICY QUESTION
> AND THIS DRAFT ASSERTS NOTHING ABOUT IT.**

A cash-secured put needs only cash and the lowest options approval. **A credit spread is a
multi-leg position that is normally a higher options level, and IRA custodians differ** — some
permit defined-risk spreads in a retirement account, some do not, and some permit them only above
an equity minimum. **None of that is measured in this repo and I am not able to verify it from
here.** `DECISIONS.md` narrows the field rather than settling it: **Tradier is closed and will not
be funded again** (2026-10-08) and **Robinhood cannot be used**, so the broker that would carry
this is not currently identified.

**SO IT IS THE REGISTER'S FIRST EXTERNAL CHECK AND IT IS A FREE KILL:** if no broker Don can use
permits spreads in his Roth at his account size, **the whole program is unbuildable regardless of
the arithmetic above, and the register should stop before the arm.** Confirming it costs one
reading of a custodian's options-agreement page and it should happen before anything is measured.
**The forward-book route is separately blocked**: the fleet's own sandbox is Tradier's.

---

## 9. ARMS, BARS AND THE TRIAL COUNT

**4 OPTIONS TRIALS, BH AT q = 0.10 ACROSS k = 4** — thresholds **0.025 / 0.05 / 0.075 / 0.10**,
membership fixed here before any arm runs. **The hurdle is DERIVED, never quoted:** options `N` is
**319** after `SELL-PREMIUM-2`, so `sqrt(2 ln N)` is **3.3956416** today and will have moved.
**Every critical value LABELLED UNCALIBRATED** (`V2G`, `R1-VAR`). Halves of the **covered
subsample** with the boundary embargoed, as four prior registers have had to do (`S18`, `U2`,
`U3`, `V6-OPT`) because the chain cache begins in 2016.

| arm | question | bar |
|---|---|---|
| **`B1`** | profitable net of **both** entry crossings **and** the assignment-band equity round trip, on capital at risk, **in both halves**? | **> 0 in both halves** — Don's clause (a) |
| **`B2`** | beats the **spread twin** on random days in the same names? | paired name-year sign test on **dollars**, **five seeds** — clause (b) |
| **`B3`** | does the spread beat the **naked** book on return per dollar of capital, paired on the identical events? | paired difference, **own se measured**, 80%-power MDE reported as `(crit + 0.84)·se` (`MB22`, `MB8`) |
| **`B4`** | does the forecast width band hold — is the realised edge positive across **5%–12.5%**? | reported as a **sensitivity with no verdict**; a width sweep is a grid and the declared rule is 7.5% |

**`K3-POS` (bar 6.0, synthetic row retained) AND `K3-ACCT` (bar 35% of the account) BOTH RUN FIRST,
IN THEIR OWN PASS**, with the arm runner **refusing** without a passing artifact (`O10`'s process
defect). **`K1` is re-measured on this register's own strike rule** — a spread needs a usable
two-sided quote on **two** legs, so its coverage is strictly worse than the short leg's 2,610, and
`O-1`'s lesson forbids inheriting it. **A coverage floor of 1,200 priceable events and 300 covered
days is pre-committed**, i.e. roughly half the naked book's, and the register **stops** below it.

---

## 10. VOID CONDITIONS, EXPECTATIONS, AND WHAT THIS DOES NOT SAY

**VOID CONDITIONS.** (1) No grid: one width rule (7.5% of spot, admissible 5%–12.5%), one strike
rule (25 delta), one tenor band, one `k`. (2) `K3-POS`'s 6.0 bar and the synthetic row may not be
relaxed; `K3-ACCT`'s 35% may not be raised — it is the incumbent's own measured exposure. (3) No
exit management of any kind; hold to expiry (§4 is why). (4) Exercising the long put on assignment
instead of selling the shares. (5) A fixed **dollar** width. (6) `K3` computed from §3's table
rather than from measured net credit. (7) Comparing this register's coverage to
`SELL-PREMIUM-2`'s 2,610 without saying they are two-leg and one-leg filters. (8) Reporting the
twin comparison on return-on-capital alone (§7). (9) Quoting any 100%-deployment row of §6 as an
offered configuration.

**EXPECTATIONS, priced now so they can be scored.**
1. **`B1` clears in both halves: 60/40.** The forecast is comfortably positive, and the model is
   optimistic in three independent ways (§3), and `SELL-PREMIUM-2`'s **late half was already
   0.82× its own detection threshold** — levering a marginal half 14× levers the uncertainty too.
2. **`B2` clears: 50/50.** The timing effect is overwhelming on the naked book, **and §3's
   reconciliation says the timing is essentially the whole of the spread's edge** — +0.3317% of
   strike is **+4.71% of the spread's capital** against a forecast +3.38%. So `B2` and `B1` are
   nearly the same question here, which makes neither a check on the other.
3. **`B3` shows the spread beating the naked book on return per dollar: 85/15.** The forecast is
   **$15.83 of P&L per trade against the naked's measured $44.70 — only 35.4% of the dollars — on
   14.20× less capital, i.e. 5.03× the return on capital.** (An earlier draft of this line said
   "~70% of the dollar P&L"; it is **35.4%**, and the corrected figure is what reproduces the
   22.99% ÷ 4.569% = 5.03× in §3's table. The direction was right and the magnitude was not.)
4. **`K3-ACCT` clears at the declared 35% cap: 90/10** — the cap enforces it by construction, so
   this is nearly tautological and is scored low-information.
5. **`K1` clears its 1,200-event floor: 55/45.** A second leg needing its own two-sided quote is
   the binding constraint and nobody has measured it.
6. **The whole register passes every leg: 30%.**
7. **Don adopts it: 10%**, and the limiting factor is §8 rather than the statistics.

**WHAT THIS DOES NOT SAY.** It is **not** a finding that spreads work — no arm has run, and
**`A3`'s level still stands**: at a fill nobody can achieve, a managed 20-delta credit spread
returned **+0.13% of max risk, PF 1.02**, negative in its first half, *"there is no premium."*
This draft's answer is that `A3` had **no dip timing** — which `SELL-PREMIUM-2` measured at
**z +9.9485** — and **four crossings with a stop** where this has two and none; **it is not that
`A3` was wrong.** It does **not** re-open `SELL-PREMIUM-2`, whose `PASSES — ELIGIBLE-BUT-UNRESOLVED`
label stands, **including the reason for the label: Stage 1 holds ZERO 30% crashes**, and a levered
short-vol book inherits that caveat **more** sharply, not less. It makes **no claim about index
spreads**. And it proposes **no trade**: `O11` binds, nothing here licenses real money, and
**adoption is Don's and is a vintage event.**

**NOT DONE:** no register committed, no arm run, no option priced, no trial booked, no
check-quadrant year read, **the broker question of §8 unresolved**, and **every return in §3 and
§6 is a forecast from Black-Scholes plus landed anchors — the register measures them or they are
nothing.**
