# PREREG DRAFT — SELL-PREMIUM-2 — the strike rule that keeps the income

**A DRAFT AND NOT A REGISTER. ZERO TRIALS.** No arm is run, no option is priced, no trial is
booked. A register is committed **ALONE** by the executor (markdown only, zero `.py`, a strict git
ancestor of every measurement commit) — `RESEARCH_CHARTER.md` §3.

**SUCCESSOR TO `SELL-PREMIUM` (`9b6986c`), AND THE CONSTRAINTS ARE THE PROMPT'S OWN:** a successor
**may change the CONSTRUCTION** and **may NOT relax the 6.0-year bar** or **drop the synthetic
single-name stress row**. Both are obeyed below. The bar stays **6.0**. The synthetic row stays and
is quoted at the predecessor's own measured value.

**EVERY NUMBER HERE IS LANDED OR IS ARITHMETIC ON LANDED NUMBERS, SHOWN IN FULL.** Sources:
`SELLPREMIUM_KILLS.json`, `V6OPT_STAGE1.json`, `V6OPT_STAGE2.json`,
`V6OPT_STAGE2_TRADES.pkl`, `OPTIONS_VRP_RESULTS.md`. **No new measurement is made.**

---

## 1. WHAT KILLED THE PREDECESSOR WAS THE INCOME, NOT THE CRASH

`SELL-PREMIUM`'s `K3` fired at **8.900816 years of premium against a bar of 6.0**, and its own
commit records the mechanism: the contracts pay **0.7777777% of strike at a median 44 DTE**, which
at the register's own `turns_per_year` of **5.7272727** (= 252/44) is **4.45455%/yr** — against the
**12.96%/yr** the draft's pre-committed table had implicitly assumed, **2.91× less**.

**THE ARITHMETIC IS EXACTLY ONE DIVISION AND IT REPRODUCES TO THE DIGIT:** the synthetic row's loss
is **39.649%** of secured cash and 39.649 / 4.45455 = **8.9008**. So the gate was decided by the
denominator.

**AND THE LOSS FIGURE PINS THE SYNTHETIC ROW'S DEFINITION, which the successor must carry
unchanged.** At moneyness *m* a cash-secured put loses `1 − (1 − x)/m` when the underlying falls
*x*. Solving `1 − (1 − x)/0.90 = 0.39649` gives **x = 0.456841**, i.e. a **45.68% single-name
fall** — 1.4× the 2020 index episode. That row is retained verbatim.

**THE CAVEAT THE PREDECESSOR SHIPPED AGAINST ITS OWN KILL, AND IT IS WHY A SUCCESSOR IS
LEGITIMATE:** on the **REAL** index episodes alone the worst is **2020 at 5.65 years, inside the
bar by 0.35**, and the gate would have **PASSED**. The synthetic row is what fired it. `W-28`
rightly forbade dropping that row after watching it fire — **and this draft does not drop it. It
changes the construction, which is the one thing a successor is permitted to change.**

---

## 2. YES, A CONSTRUCTION EXISTS THAT CLEARS `K3` ON ITS OWN MEASURED INCOME

**THE INSTRUMENT IS CALIBRATED TO THE PREDECESSOR'S OWN MEASUREMENT, NOT BORROWED** (`MB8`: never
borrow a number across populations). Solving Black-Scholes for the implied volatility that
reproduces **0.7777777% of strike at m = 0.90 and T = 44/365** gives **IV = 0.2864** — a low-vol
figure, consistent with a 2016–2019 build quadrant, and **materially below `V6-OPT`'s measured
post-dip 0.430 on its own 2016–2025 population.** Using `V6-OPT`'s income figure here would have
been the borrowed-number error; this is the predecessor's own.

**THE INSTRUMENT CHECK, BEFORE ANY CONCLUSION (`MB15`): at m = 0.90 this calibration reproduces
the predecessor's published 2020 row at 5.64 years against its measured 5.65.** Two decimals, on a
row the predecessor published and this draft did not fit to.

Walking the strike at that IV, 44 DTE, `turns_per_year` 5.7273, loss `1 − (1 − x)/m`:

| moneyness | put delta | premium / strike | **income / yr** | synthetic-row loss | **years of premium** |
|---|---|---|---|---|---|
| 0.800 | −0.011 | 0.048% | 0.274% | 32.06% | 117.09 |
| 0.850 | −0.046 | 0.231% | 1.322% | 36.06% | 27.29 |
| 0.875 | −0.082 | 0.441% | 2.526% | 37.89% | 15.00 |
| **0.900** — what ran | **−0.134** | **0.778%** | **4.455%** | **39.61%** | **8.89 FIRES** |
| **0.925** — ≈ 25 delta | **−0.202** | **1.277%** | **7.315%** | **41.24%** | **5.64 CLEARS** |
| 0.950 | −0.286 | 1.967% | 11.267% | 42.79% | 3.80 CLEARS |
| 0.975 | −0.380 | 2.863% | 16.398% | 44.26% | 2.70 CLEARS |
| 1.000 | −0.480 | 3.965% | 22.709% | 45.65% | 2.01 CLEARS |

> **THE ASYMMETRY IS THE WHOLE ANSWER. MOVING THE STRIKE TOWARD THE MONEY RAISES INCOME CONVEXLY
> AND RAISES THE CRASH LOSS ONLY LINEARLY AND SLOWLY.** From 0.90 to 0.925 — a quarter of one
> percent of spot — income rises **+64%** while the synthetic loss rises **1.63pp**. The crash loss
> is dominated by the *fall*, not by the strike: `dL/dm = (1 − x)/m² = 0.635`, so a strike move of
> 0.025 can only move the loss by 1.6pp, while the premium at that moneyness is still steeply
> convex in it.

**SO THE PREDECESSOR'S 0.90 RULE SAT IN THE WORST PART OF THE CURVE** — far enough out to have
surrendered most of the income, not far enough out for the loss reduction to pay for it.

---

## 3. THE DECLARED CONSTRUCTION: **25-DELTA TARGETED**, AND WHY THAT ONE

**ONE STRIKE RULE. NO GRID.** §2 shows a whole range clears; declaring the range would be the grid
search `RESEARCH_CHARTER.md` forbids, and picking the cell with the most headroom after computing
the table is choosing the design on the arithmetic.

**THE RULE IS `V6-OPT`'s: the put nearest 25 delta, solved on the PUT leg**, tenor band **20–60
DTE** (the predecessor's own band, kept so the comparison is clean), **held to expiry**.
**Three reasons, in order of weight:**

1. **IT IS THE ONLY STRIKE RULE IN THE RANGE WITH A MEASURED PRIOR.** `V6-OPT` banked
   **+1.1342%/trade on secured cash, positive in both halves, 84.39% wins, 25.30% assignment, and
   a paired name-year sign test against a random-day twin at z +7.2506 (306 of 457 cells)** — all
   at 25 delta. Moneyness 0.950 clears `K3` with more room and has **no measured prior at all.**
2. **ITS ASSIGNMENT RATE IS THE ONE THE RECORD HAS MEASURED.** At the calibrated IV a 25-delta put
   sits at **m ≈ 0.925 and delta −0.202**, against `V6-OPT`'s measured median **−0.2638** and
   **25.30%** assignment. Past about 0.95 the delta passes −0.29 and by 1.00 it is −0.48, i.e.
   **assignment becomes a coin flip and "selling premium" stops being the right description of
   the trade.** That is the real ceiling on §2's range and it is not a return argument.
3. **A DELTA TARGET IS INVARIANT TO THE VOLATILITY REGIME AND A MONEYNESS TARGET IS NOT.** At fixed
   0.90 moneyness the premium runs **0.272% of strike at IV 0.25 and 5.359% at IV 0.80** — a
   twenty-fold swing in position size driven by nothing but the regime. A delta target holds the
   per-position risk roughly constant across regimes. **That is a feature for a rule that must
   survive an unknown crash and a defect only for a rule trying to discriminate risk** — see §4.

**THE EXPECTED `K3` READING IS 5.64 YEARS AGAINST THE 6.0 BAR, AND THAT IS A KNIFE EDGE —
DECLARED NOW, BEFORE THE MEASUREMENT.** 6% of headroom. `E-6` recorded that *"a successor must not
set a knife-edge burn-in bar"* and `W-1`'s `K1` died on a 0.10pp knife edge; this register sits on
one and says so first. **The consequences are pre-committed both ways:**

* **If `K3` fires at 25 delta, the FAMILY CLOSES.** The income/crash trade-off then has no solution
  on this event at any strike a premium-selling book can hold: further out fails on income (§2's
  top rows), further in fails on assignment (§3.2). **No third strike rule is proposed, then or
  ever, and this draft says so before knowing the answer.**
* **The bar is NOT relaxed and the synthetic row is NOT dropped**, whichever way it lands.
* **The direction of the arithmetic error is named:** §2's income curve is **mid-based** at the
  calibrated IV while the predecessor's 0.7778% was measured **net of a touch crossing**. Since the
  absolute half-spread is roughly constant in dollars, it is a **smaller fraction of a larger
  premium**, so the curve **understates** income at higher moneyness. **The error runs toward
  clearing, so it is disclosed rather than relied on, and `K3` is computed on the register's OWN
  measured net income at its OWN strike rule — never on this table.**

---

## 4. WHAT THIS CONSTRUCTION GIVES UP, AND WHY DON'S RULING MAKES IT FREE

**`V6-OPT`'s AUTOPSY IS CORRECT AND THIS REGISTER DOES NOT DISPUTE IT.** A delta target sets the
strike from the name's own volatility, so it **equalises assignment probability by construction**:
`V6-OPT` measured **25.303% healthy against 25.727% unhealthy — a 0.43pp gap** where `V6-B` had
measured a real risk difference of **2.797pp on the same covered rows** (10.84pp on the full
panel). **A risk signal cannot pay through a delta-targeted strike.** That is why the predecessor
went to fixed moneyness.

**AND IT IS NOW A COST WITH NOTHING TO BUY, BECAUSE DON REMOVED THE CONDITION IT WAS PAYING FOR.**
`DECISIONS.md` **2026-10-12**: an options strategy *"is judged as its own system"* and passes if it
is **profitable net of realistic costs on the capital it ties up, in both halves**; **beats the
same trade on random days in the same names**; and **survives realistic sizing and concurrency
(`O11`) and the pre-committed crash stress.** **There is no health-discrimination condition in that
list, and the shares comparison "is REPORTED for context and carries no verdict."**

> **SO THE ONLY THING THE MONEYNESS RULE BOUGHT IS NO LONGER ON THE PASS LIST, AND IT COST 2.91× OF
> THE INCOME AND THE `K3` GATE.** Reverting the strike rule is not a relaxation of a bar; it is
> declining to keep paying for a condition the owner has withdrawn.

**STATED AGAINST ITSELF, BECAUSE IT IS THE REAL LIMITATION: this register cannot become a
risk-selection product.** At 25 delta a healthy dip and an unhealthy dip are sold at the same
assignment probability, so the book is **a premium-selling book that happens to enter on dips**,
not a book that picks the safe dips. `V6-OPT` established that and it is inherited rather than
re-litigated. **Anyone wanting the risk-selection version is back at fixed moneyness and back at
`K3`, which is now a measured dead end rather than an open question.**

---

## 5. WHAT CARRIES OVER UNCHANGED, AND WHAT MUST BE RE-MEASURED

**CARRIES OVER — the predecessor's kills already cleared and are not re-run:**

* **`K1` COVERAGE CLEARED BY 6.4× AND 4.1×** — **2,557 priceable events against a 400 floor** and
  **612 covered event days against 150**, over **186 covered names**, from a funnel of 4,864 events
  → 2,645 with a chain file → 2,622 in the DTE band → 2,612 in moneyness → **2,557 two-sided**.
  **A 25-delta rule searches the whole chain for a delta rather than a fixed band, so its coverage
  is weakly BETTER than the moneyness rule's** — but it is a **different filter** and `K1` is
  therefore **re-measured on this register's own strike rule** (`O-1`'s lesson: coverage is
  measured on the arm's own population, never inherited).
* **`K2` CLEARED AND ITS FINDING IS THE REASON THIS REGISTER IS WORTH RUNNING.** Re-pricing `A3`'s
  own **881** era trades as **naked puts held to expiry at the MID** (coverage **1.0000**, zero
  skipped) gives **+0.5700 / +0.4904 / +0.4229 % of strike** across `A3`'s own IV-rank bands — a
  gradient of **−0.1471pp** against `A3`'s banked **spread** gradient of **−3.21pp**, **flatter by
  21.8×, and every band POSITIVE** where the spread reads −6.24 / −8.16 / −9.45 % of max risk.
  **`A3`'s monotone gradient is a property of a $5-wide stopped spread, not of the premium.**
* **AND `K2`'s OTHER HALF, WHICH CUTS AGAINST THIS REGISTER AND SHIPS WITH IT:** the **medians rise**
  with IV rank (0.9018 → 1.0409) while the **means fall** and the **sd widens** (1.758 → 2.858).
  That is the short-vol signature, and it is the same fact as `K3` seen twice. **A book with a
  per-trade MEAN bar is judged on the falling statistic.**
* **`A3`'s LEVEL IS UNTOUCHED AND REMAINS THE STRONGEST FACT AGAINST THIS PROGRAM.** At aggression
  0.00 — perfect mid on both legs both ways — `A3` returns **+0.13%, profit factor 1.02**, against
  a 1.20 bar, **negative in its first half**: *"there is no premium being lost to execution here,
  because there is no premium."* **This register's answer is that `K2` measured the naked level
  POSITIVE in all three bands on `A3`'s own trades, and that is a measured answer rather than an
  argument — but it is `A3`'s instrument re-read, not an independent one.**
* **THE SPLIT TRAP, IN BOTH DIRECTIONS AND IN THE RIGHT PLACES.** The **EVENT** is defined on the
  **adjusted** series (`V6`'s `C5`: a 2-for-1 split reads as −50% on a raw series, and companies
  split *after* they rise); the **STRIKE, the moneyness test and the settlement** use the
  **as-traded** series (`O-1`'s MNST 3-for-1 booked a fake +1453%). **The predecessor measured what
  getting this wrong costs: ~71% of the gap between the scout draft's coverage estimate and its own
  — AAPL 2018-01-02 reads 40.234 adjusted against 172.260 as-traded, a factor of 4.28.** That
  defect was in the scout's own funnel, which is why it is pinned here rather than assumed.
* **THE VACUITY TRAP, RECORDED BY THE PREDECESSOR AND INHERITED:** `options_derived` is two-sided
  on **1.0000** of its rows **BY CONSTRUCTION**, so a quote-coverage funnel measured there reads
  1.000 having checked nothing (`MB21`'s `C1`). **The funnel and the traded quote read the RAW
  layer.**

**MUST BE RE-MEASURED, because the strike rule changed:** `K1` (above), the **net income at 25
delta** (which is `K3`'s denominator and may not come from §2's table), the **median DTE and
`turns_per_year`**, the **assignment rate**, and the **per-trade SD** that sets every MDE
(`MB8`: an se may not travel across perturbation sizes, and a strike change is one).

---

## 6. THE ARMS, THE BARS, AND THE TRIAL COUNT

**4 OPTIONS TRIALS, BH AT q = 0.10 ACROSS k = 4** — thresholds **0.025 / 0.05 / 0.075 / 0.10**,
membership fixed here before any arm runs. **The hurdle is DERIVED, never quoted:** options `N` is
**315** after the predecessor's five trials, so `sqrt(2 ln N)` is **3.3919235** today and will have
moved by the time the register is written. **Every critical value LABELLED UNCALIBRATED** (`V2G`,
`R1-VAR`: no calibrated floor exists for a paired within-panel difference, and `UNIVERSE-BIAS`
means no `X7` floor transfers to this universe).

**EVENT, unchanged from the predecessor and not re-chosen:** a daily return at or below **−2.5×**
the name's own trailing 60-session return volatility taken `shift(1)`, on the **point-in-time**
$10B tier at the event date — never ever-in-tier. **Build quadrant ∩ options era: 2016–2019 ×
ticker half 0.** Halves are of the **covered subsample** with the boundary embargoed, because the
options cache begins in 2016 and the charter's 2009–2014 half is structurally empty (`S18`, `U2`,
`U3`, `V6-OPT`: the same substitution, four times).

| arm | question | bar |
|---|---|---|
| **`A1`** | Is it profitable net of a full touch crossing at entry, on secured cash, **in both halves**? | **> 0 in both halves** — Don's clause (a). A short put held to expiry crosses **once**, not twice (`MA46`) |
| **`A2`** | Does it beat the **same trade on random days in the same names**? | paired **name-year sign test**, **five seeds minimum** (one seed flipped `R2`'s verdict) — Don's clause (b) |
| **`A3′`** | Does the **25-delta** rule beat the predecessor's **0.90-moneyness** rule on the identical events? | **paired** difference, **own se measured**, own MDE reported at **80% power** = `(crit + 0.84)·se` (`MB22`) |
| **`A4`** | Does **health** discriminate at 25 delta? | **Expected NO**, and it is run to close the question rather than open it — `V6-OPT` measured the 0.43pp assignment gap and §4 explains it. **A null here is the prediction, not a disappointment** |

**`K3` IS THE GATE AND IT RUNS FIRST, IN ITS OWN PASS**, with the arm runner **refusing** without a
passing artifact (`O10`'s process defect: *"C2 and the outcome statistics were computed in the SAME
pass, so it cannot be claimed the control was read before the numbers"*). **Bar 6.0, synthetic row
retained, both unchanged from the predecessor.**

**SURVIVABILITY — Don's clause (c).** `O11`'s grid, **$25k / $50k / $100k / $250k × cap 10 / 50**,
with the **affordability** skip and the **concurrency** skip as **separate recorded fields**
(`MB3`: *"the low-end failures are AFFORDABILITY, not ruin — the book never gets on"*). A
cash-secured put on the tier's median share price of **$49.01** ties up **$4,411 per contract**, so
cap 10 needs about **$44,100** and the **p95 name at $160.64 needs $14,458 per contract**, i.e.
**$144,576** for cap 10. **And the drawdown must be CAPITAL-WEIGHTED**, because `V6OPT_STAGE2.json`
says of its own −55.52% figure: *"it is NOT a capital-weighted portfolio equity curve … so it
OVERSTATES drawdown."*

**THE SHARES COMPARISON IS REPORTED AND CARRIES NO VERDICT** — Don's 2026-10-12 ruling, verbatim.
`V6-OPT` measured the stock at **+3.4269%/trade** against the put's **+1.1342%**, and a regression
of the put's return on the stock's over its 660 banked trades gives a realised exposure of
**0.2131** with an option-specific intercept of **+0.4040pp** (*t* 2.55 pooled, about **1.73** once
haircut by `R3`'s measured options design effect of 2.21, so **no verdict** there either).
**Reported, labelled, and not a bar.**

---

## 7. VOID CONDITIONS, EXPECTATIONS, AND WHAT THIS DOES NOT SAY

**VOID CONDITIONS.** (1) **No grid**: one strike rule (25 delta), one tenor band (20–60 DTE), one
`k` (2.5). (2) **The 6.0 bar may not be relaxed and the synthetic row may not be dropped.** (3) No
third strike rule if `K3` fires — the family closes. (4) `K3` may **not** be computed from §2's
mid-based table; it uses the register's own measured net income. (5) Quoting `V6-OPT`'s income or
SD as this register's own — they are a different population and a different era (`MB8`). (6)
Quoting `A3`'s **−7.99% of max risk** against any **% of secured cash** figure as commensurable.
(7) Reading a `K3` pass as evidence the book survives a crash — `K3` is a *stress arithmetic*, not
an outcome. (8) Treating `A4`'s expected null as a failure.

**EXPECTATIONS, priced now so they can be scored.**
1. **`K3` clears at 25 delta: 60/40.** The arithmetic says 5.64 against 6.0, and 6% of headroom is
   not much against a measured-income figure that could land either side.
2. **`A1` clears in both halves: 75/25.** `V6-OPT` measured both halves positive (+1.1348 /
   +1.1178) on a different event at this strike rule.
3. **`A2` clears: 55/45.** `V6-OPT`'s z +7.2506 was on the **drawdown** event; this is the **acute
   shock** event and the control is the same trade on a random day, which is a hard comparator.
4. **`A3′` shows 25 delta beating 0.90 moneyness on return: 80/20.** The income difference is 64%
   of a small number and the paired se will be small, so this is the most likely clear pass.
5. **`A4` finds health NOT discriminating: 70/30**, i.e. the autopsy holds at 25 delta.
6. **The whole register passes every leg: 30%.** Four arms and a gate, and the gate is a knife edge.
7. **My prior that Don adopts it: 15%**, against 10% for the predecessor — the difference is
   entirely the 2026-10-12 ruling removing the shares margin.

**WHAT THIS DOES NOT SAY.** It is **not** a finding that selling premium after a drop works — no
arm has run. It does **not** reopen `V6-OPT`, whose rejection stands on its own pre-committed
condition 2, and it does **not** claim that condition was wrong — only that Don has removed it from
the pass list. It does **not** weaken `SELL-PREMIUM`: its `K3` was correctly computed, correctly
fired, and its five trials correctly **stay charged** (`E-1`, `MA6`), and this register inherits
its coverage and its premise findings rather than re-running them. It makes **no claim about index
options**, where the variance risk premium is a different and far better-documented object. And it
proposes **no trade**: `O11` binds, nothing here licenses real money, and **adoption is Don's and
is a vintage event.**

**NOT DONE:** no register committed, no arm run, no option priced, no trial booked, no
check-quadrant year read, and **`K3`'s income is a forecast until the register measures it.**
