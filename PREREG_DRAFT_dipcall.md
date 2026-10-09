# PREREG DRAFT — DIP-CALL — calls after a sharp drop in a strong, liquid company

**A DRAFT AND NOT A REGISTER. ZERO TRIALS.** No arm is run, no forward return is scored, no option
is priced, no trial is booked. A register is committed **ALONE** by the executor (markdown only,
zero `.py`, a strict git ancestor of every measurement commit) — `RESEARCH_CHARTER.md` §3.

**Authorised by Don, `DECISIONS.md` 2026-10-08:** *"calls after a sharp drop in a strong, liquid
company is authorised as a research program — stock-level bounce first, the option expression only
if the bounce survives, then a forward paper book. Same discipline as all research; no real
trades."*

**One measurement IS in this draft and it is a feasibility CENSUS, declared as such:** §1 counts
how many events exist and how clustered they are. **No forward return is touched anywhere** — the
event-day return defines the event and nothing after it is loaded. A census is a fact about what
data exists (`S25`/`MB15`/`MB3`, all logged at zero trials) and under `MB1-SEL` can only ever
**BLOCK** this program, never produce a finding for it.

---

## 1. POWER FIRST — and unlike `DC-1` this program is powered, but only at SHORT horizons

`DC-1` died because its event count could not resolve the effect. **The prompt asks whether that
happens here. It does not — provided the horizon is short — and that is the single most important
sentence in this draft.**

### 1a. THE EVENT CENSUS, measured on the build quadrant

Build quadrant = **2009–2019 × `stable_key_half(ticker) == 0`**, on the corrected full raw
universe (`UNIVERSE_BIAS_PANEL_full.pkl`). Tier = **ever `market_cap >= $10B`** on a
build-quadrant date, which is **459 of 3,545** half-0 names; **458** have a price file.

Event = a daily return at or below **−k × the name's own trailing 60-session return volatility**,
the volatility taken **strictly prior** (`shift(1)`) so the event day is not inside its own scale.
**1,073,204 scoreable name-days over 2,727 sessions.**

| k | events | rate per name-day | distinct event days | worst single day | worst 10 days | eff-n at ρ=1 |
|---|---|---|---|---|---|---|
| 2.0 | **28,646** | 0.0267 | 2,416 | 1.25% | 9.18% | 2,416 |
| **2.5** | **14,727** | 0.0137 | 2,086 | 2.35% | 14.05% | **2,086** |
| 3.0 | **8,296** | 0.0077 | 1,773 | 3.85% | 18.18% | 1,773 |

**THE CLUSTERING IS FAR MILDER THAN THE DESIGN FEARED, AND THAT IS THE RESULT THAT MAKES THIS
PROGRAM VIABLE.** A volatility-relative threshold does **not** collapse into a handful of
market-wide crash days: at k = 2.5 the worst single day carries **2.35%** of all events and the
worst ten carry **14.05%**. Compare `SELRULE`, where 16 co-moving countries were worth **2–4**
independent draws and quoting 16 would have understated the true α **7.5-fold**.

**The honest figure is a BRACKET, not a number**, and every power statement below uses both ends:

* **lower (pessimistic, ρ = 1)** — every event on a given day shares one shock entirely, so the
  effective n is the number of **distinct event days**: **2,086** at k = 2.5.
* **upper (raw)** — events are independent: **14,727** at k = 2.5.

**THE REGISTER MUST MEASURE THE DESIGN EFFECT RATHER THAN ASSUME EITHER END**, against its own
shuffled null, because `R3` established that **a raw design effect is not evidence of clustering**:
600 independent draws in 12 blocks returned a design effect near 1.8 from sampling error alone, and
applying it as a haircut would have manufactured a correction out of noise.

### 1b. REQUIRED EVENTS, at the honest hurdle, by horizon

`MB22`'s gate: the 80%-power MDE is `(crit + 0.84) · se`, **not** `crit · se` — every MDE this
project published before `MB22` was a **50%-power** figure. Critical value is the Harvey-Liu-Zhu
hurdle, **derived not quoted**: equity `N` = 274 → **3.3505606**.

Single-name abnormal-return dispersion scales as `√horizon`. **The 63-session SD is the one number
below that is an ANCHOR TO BE MEASURED, not a measurement** — it is set at 20pp for this
arithmetic and the register must measure it on the arm's own rows before any bar is fixed.

| horizon | SD (pp) | +0.25pp | +0.5pp | **+1.0pp** | +2.0pp |
|---|---|---|---|---|---|
| **5 sessions** | 5.63 | 8,920 | **2,230** | **557** | 139 |
| **21 sessions** | 11.55 | 37,463 | 9,366 | **2,341** | 585 |
| 63 sessions | 20.00 | 112,389 | 28,097 | 7,024 | 1,756 |
| 126 sessions | 28.28 | 224,778 | 56,195 | 14,049 | 3,512 |

### 1c. THE VERDICT ON POWER, STEP BY STEP

**STEP 1 IS POWERED AT 5 AND 21 SESSIONS AND IS NOT POWERED AT 63 OR 126.**

* At **5 sessions**: +0.5pp needs **2,230** against a bracket of **[2,086, 14,727]** — reachable at
  the pessimistic end to within 7%, comfortable on the raw count. +1.0pp needs **557**: powered
  under any clustering assumption.
* At **21 sessions**: +1.0pp needs **2,341** against **[2,086, 14,727]** — marginal at the
  pessimistic end, comfortable on raw. +2.0pp needs **585**: powered either way.
* At **63 sessions**: +1.0pp needs **7,024** — raw-count only. **And the record's own banked dip
  effect is +0.5203pp over 63 days (`V6`'s A3, via `DC-1`), which needs 28,097 and is NOT
  REACHABLE at any k.**
* At **126 sessions**: nothing the record has seen is detectable.

**SO THE PROGRAM HAS POWER EXACTLY WHERE THE REVERSAL LITERATURE PUTS THE EFFECT, AND LOSES IT
EXACTLY WHERE `V6` AND `DC-1` LOOKED.** That is the difference from `DC-1` in one line: `DC-1`
needed ~3,098 effective events at 80% power against **400** available — **7.7× short** — and this
census has **2,086 to 14,727**.

**STEP 2 IS POWERED ONLY FOR A LARGE OPTION EFFECT, AND THE BINDING CONSTRAINT IS COVERAGE.**
Per-trade option return dispersion is **92.51pp** (`EVOWN`'s banked sd 0.9251 on 4,754 trades).
Options hurdle at `N` = 310 → **3.3872031**.

| option effect | independent trades needed at 80% power |
|---|---|
| +5pp | 6,117 |
| +10pp | 1,529 |
| +20pp | 382 |
| +30pp | 170 |

**And `O17C4`'s measured option effect for a related strategy — calls owning an earnings event —
was +4.79pp, which needs 6,665 trades.** Measured availability inside the window where options
exist at all:

| k | events 2009–2019 | **2016–2019 (priceable)** | 2016–2018 (Tier E past 200 DTE) | distinct days |
|---|---|---|---|---|
| 2.0 | 28,646 | **11,822** | 9,296 | 923 |
| 2.5 | 14,727 | **6,390** | 5,127 | 826 |
| 3.0 | 8,296 | **3,709** | 3,046 | 738 |

**BEFORE ANY CHAIN-COVERAGE HAIRCUT**, k = 2.5 offers 6,390 priceable events. **After one it will
be far fewer**: `O-1` measured the harvest freeze reaching **6,711 of 113,945 panel cells = 5.89%**,
with **775 of 2,531 panel names present but only 421** also carrying a populated bars file.
Coverage on the **$10B tier** should be much better than 5.89% — options exist on large caps — **but
it is UNMEASURED, and §4a makes measuring it the first thing step 2 does.**

**The honest statement: step 2 can confirm an option effect of roughly +13pp or larger and cannot
resolve the +5pp that `O17C4` measured for its cousin.** That is a reason to design step 2's
hurdle around the implied-volatility question rather than around a thin edge — see §4c.

---

## 2. WHY THIS IS NOT A RE-RUN — item by item, as the prompt requires

| item | what it found | why DIP-CALL differs |
|---|---|---|
| **`V6`** | four NULLs on healthy 20%/30% drawdowns from a 252-day high at 63d/126d; **Spearman(drawdown, `momentum`) = +0.6642**, so *"a drawdown is substantially an inverse-momentum sort"*; 7 of 8 leg-series flip sign between halves | **Different event, different horizon, different scale.** A 252-day drawdown is a slow state and is largely inverse momentum; a **−2.5σ single session** is a shock. `V6`'s MDE was **+3.371pp** at its own bar — it could not have seen a 1pp effect either. DIP-CALL's primary horizons are **5 and 21 sessions**, which `V6` never read. |
| **`V6-B`** | healthy dips fall a further −20% **less often** — 32.51% vs 43.35%, **−10.228pp at HAC *t* −10.5847**; a **RISK** result | **Carried forward as a prior, not re-tested.** It says the downside is thinner after a healthy dip; it says **nothing about return**, and its own caveat binds: the gradient runs **−14.287pp in the smallest quintile against −3.787pp in megacaps**, so it is *"strongest exactly where the product is not"* — and DIP-CALL is a **$10B-tier** program. |
| **`V6-OPT`** | cash-secured puts on healthy dips **REJECTED** — healthy +1.1342%/trade vs **unhealthy +1.2651%**, so the health floors did no work; assignment 25.30% vs 25.73% | **Opposite side of the book and the mechanism that killed it does not apply.** `V6-OPT` sold a **delta-targeted** put, and *"a delta-targeted rule sets the strike from the name's own volatility, so it neutralises the very risk difference the trade was built to exploit."* DIP-CALL **buys** and §4b fixes **moneyness** as well as delta, specifically so that neutralisation cannot recur. |
| **`DC-1`** | killed at **feasibility**: needed ~3,098 effective events at 80% power against **400** — 7.7× short; measured k median **2.9061** against a required **≤1.8058** | **This is the same question with ~5–37× the events**, because the event is volatility-relative and one session rather than a 30% drawdown. **Its provenance note binds and is honoured in §6.** |
| **`O17C4`** | calls spanning earnings **+10.30% vs +5.50%** random entry = **+4.79pp**, both halves, z +2.054; but **DTE-matched median-vs-median +0.40pp** — the typical trade is a near-total loss either way | **The closest living relative, and the reason step 2 is a MEAN test with a median reported beside it.** `O17C4` also found **alert-spanning LOSES to random-spanning** (z −4.4726), which is why DIP-CALL's entry is a **price event**, never an alert. |
| **`O13`** | expectancy rises with tenor, −0.35% → +7.63%; q2 gap −10.84pp — **but FAILS its own calibrated bar** (0.472 vs p95 0.497) and clears one half only. *"Do not act on it."* | **Not relied on.** Step 2's tenor grid is fixed on **data coverage** (§4a), not on `O13`'s gradient, and the draft does not cite it as support. |
| **`R2`** | the alert book loses to random entry by **−5.0640pp**; sign test z −4.9612, p 7e−07 | **DIP-CALL does not use the alert at all.** `R2`'s *method* — a random-entry control on the same names — is adopted as step 2's primary control. |
| **`DEEPITM-FIN` / `SC-3`** | all-in long-dated call financing **701.87 bps/yr** at 60–90 DTE; `SC-3` **NO-FLIP in all four strata**, 915.4 / 798.0 / 676.5 / 757.9 bps at 200–858 DTE, every interval above Gold's rf+420 | **A cost input, charged, not a question re-asked.** Neither is re-derived (`MB4`'s rule: *"nobody should spend a trial re-deriving this"*). `SC-3`'s binding limitation travels: **Tier E reaches past 200 DTE for 2016–2018 only**, a near-zero-`rf` regime, so era-robustness at long tenor is unmeasured. |
| **`O10`/`O18`** | a real trade pays **ρ = 0.6743** of the quoted half-spread [0.6617, 0.6871]; passive net saving **+0.6318pp** with adverse selection eating **74.3%** of the gross | **Used as the fill convention**, labelled an extrapolation (ρ was measured on 35-delta ~60-DTE **calls**, which is close to step 2's grid but not identical). The headline is taken at **full quoted spread**, with ρ beside it. |
| **`O11`** | a **+3.27%/trade positive-expectancy** book ends at **$37,059 from $50,000** at cap 10; expectancy **−4.51% in quiet weeks vs +14.28%** in the top decile; 51.5% of trades in weeks of >10 alerts | **Governs step 3 and is the reason step 2 is not the end.** `O11` is why a per-trade edge is not a product, and **dip events cluster by construction** (§1a), so the concurrency problem is *structurally worse* here than for the alert book. **Step 3 must report survivability, not expectancy alone.** |
| **`P1S0`** | the equity composite sorts the optionable universe **only after 2021** — H=63 early *t* **0.8352** against a floor of 1.6974 | **Binds the "rock solid" condition.** The quality/health overlay in §3c is therefore a **declared sensitivity, never the primary**: conditioning on a composite that does not sort this universe pre-2021 would import `P1S0`'s failure into the event definition. |

---

## 3. STEP 1 — DOES THE STOCK BOUNCE? *(equity data, cheap, and it can stop the program)*

### 3a. The event, fixed here

`r_t <= -k · σ_{t-1}`, where `σ` is the trailing **60-session** standard deviation of daily
returns taken **strictly before** the event day, with a **40-observation** minimum.
**PRIMARY: k = 2.5 over a 1-session window.**

**VOLATILITY-RELATIVE IS THE POINT AND IT IS WHY A FLAT PERCENTAGE IS REFUSED.** A 3% day is
ordinary for a high-vol name and extreme for a staple; a flat threshold would make the event a
**volatility sort wearing a dip's name**, which is `V6`'s inverse-momentum finding waiting to
recur.

**THE PRICE BASIS IS SPLIT- AND DIVIDEND-ADJUSTED FOR THE EVENT AND MUST BE RAW FOR ANY STRIKE.**
`V6`'s `C5` pinned both sides: on a raw series a 2-for-1 split reads as a −50% drawdown, and since
companies split **after** they rise, a raw basis flags the strongest names in the universe. `O-1`
then paid the other half of the lesson — **MNST's 3-for-1 booked a fake +1453%** because strikes
are as-traded while `raw_close` crosses the split. **So: adjusted for the event (step 1), raw for
the strike (step 2), and the shipped split guard passed explicitly rather than left to default**,
because *"a guard whose default is OFF for backward compatibility is a guard a new caller silently
loses."*

### 3b. The news split is also a POWER split, which is the part worth knowing

Chan (2003) finds **no-news** price shocks tend to **reverse**; Savor (2012) finds **information**
shocks **drift**. Pooling them can cancel both, so they are **two arms and never one**.

**AND THE SPLIT DOES MORE THAN THAT.** An earnings-dated drop is **idiosyncratic** — a name's
reporting date is its own — so those events are spread across the calendar and are closer to
independent. A no-news drop is far more likely to be market-driven and therefore clustered. **So
the news arm is the better-powered subsample and the no-news arm is where the clustering haircut
bites hardest**, and each arm's design effect must be measured separately rather than pooled.

**News is defined from `EVENTS` code 22 (earnings) plus the dated event codes**, with
`SHARADAR_REFERENCE.md`'s 37-code legend — **and `SC-2`'s correction travels**: that legend has
been in-tree since `47cb189`, so `S17`'s *"tested by number, unlabelled"* does not recur.
**Coverage is a declared kill (§3e), because `O6`/`O7` measured 29 of 186 names as foreign private
issuers with ZERO earnings dates — a filter reading "no date" as "no announcement" fails OPEN on a
non-random tenth of the book.**

### 3c. The "rock solid" condition is a SENSITIVITY, not the primary

Don's words are *"an extremely liquid, rock-solid company"*. The tier (`cap >= $10B`) carries
**liquidity**; the quality overlay carries **"rock solid"** — and it is **not** in the primary,
for a measured reason: `P1S0` found the composite does not sort the optionable universe before
2021, and `V6-OPT` found the health floors **did no work at all** on exactly this kind of dip
population (healthy +1.1342% against unhealthy **+1.2651%**). **Conditioning the primary on a
score that has twice failed on adjacent populations would import those failures into the event
definition.** It is read as a labelled sensitivity carrying no verdict.

### 3d. Statistic, controls and bars

* **Statistic:** mean abnormal return over the horizon, abnormal measured **two ways, both
  reported**: against the name's **own** trailing mean (its "normal" return) and against the
  **market** (the panel's own value-weighted return, built from panel prices — Ken French is used
  **nowhere**, because it is *"free but permission-gated and factor-level — never a magnitude
  claim"*). **`DC-1` measured these disagreeing in sign** — +0.5203pp vs own-normal against
  **−0.1200pp** vs-universe — so **quoting one alone is forbidden.**
* **PRIMARY HORIZON: 21 sessions**, with **5 sessions co-primary**. 63 and 126 are **sensitivities
  carrying no verdict**, and the draft says why in advance: §1c shows power dies there, and they
  are where `V6` and `DC-1` already looked.
* **Both halves inside the build quadrant** — 2009–2014 / 2015–2019, boundary embargoed. An arm
  clearing one half is `NOT_REPLICATED`.
* **The bar is the arm's own within-date permutation p95**, not a borrowed floor. `V2G` and
  `R1-VAR` established there is **no calibrated floor for a paired within-panel difference**, and
  `CORRECTED-FLOORS` part 1's seven floors are calibrated on **quarterly decile books**, not on
  daily event studies — so every critical value here is **LABELLED UNCALIBRATED**.
* **NO SURVIVOR FILTERING.** Drops that kept falling stay in: 2008–09 and 2020 and 2022 are inside
  or adjacent to the window, and `E-5` measured what dropping them costs — **591 rows whose ticker
  stops trading inside the window silently deleted 16 crashes, 5 of them flagged.** A delisted name
  has a **terminal** value (`last_close / c0 − 1`, which `E-5` verified reproduces the panel's own
  `fwd_ret` at max |Δ| 0.000e+00 on 591 of 591 rows); an **administrative** end of data still
  censors. Those two causes are not the same and the register must separate them.

### 3e. Step 1's free pre-outcome kills

1. **Event count on the arm's own rows** must leave **≥ 1,500 events** in **each** news arm in
   **each** half — the floor derived from §1b (+2.0pp at 21 sessions needs 585; +1.0pp needs
   2,341), declared now so it cannot be relaxed after a thin cell appears.

   **DISCLOSED, BECAUSE THIS IS THE ONE PLACE THE DRAFT'S OWN ORDERING IS IMPERFECT: the 1,500
   was written with §1a's census already in view.** The project's register guard exists to stop
   exactly that — a threshold fixed after a number is known — so the reader is owed the fact
   rather than left to spot it. **Two things bound it. (a) The floor is DERIVED from the power
   table, which does not depend on the census at all**: it sits between the 585 needed for
   +2.0pp and the 2,341 needed for +1.0pp at the primary 21-session horizon, so it is a power
   statement rather than a count-fitting one. **(b) An event COUNT is not an OUTCOME.** Nothing
   in §1a reads a forward return, so knowing how many events exist cannot tell anyone which way
   an arm will go — which is the thing the guard protects. **A stricter reader may still discount
   this floor, and the register may raise it but may never lower it** (`W-28`).
2. **Earnings-date coverage ≥ 0.70** of tier names, with names carrying **zero** earnings dates
   **counted and excluded by name**, never read as "no news".
3. **The design effect measured against its own shuffled null** (`R3`), and the register reports
   the effective-n **bracket** rather than either end.
4. **The event must not be a volatility sort**: mean per-date |ρ| between the event flag and the
   name's own trailing volatility rank must be **< 0.30**. If a −2.5σ day is just "this is a
   volatile name", the arm is `INERT`.

---

## 4. STEP 2 — IS A CALL THE RIGHT WAY TO OWN IT? *(only if step 1 passes)*

### 4a. COVERAGE IS CENSUSED FIRST, BEFORE ANY PRICE IS READ

The prompt requires this and the record is unambiguous about why. **Stated before any number:**

* The derived options layer spans **2016-01-04 → 2025-12-31** (`U2`), so of the build quadrant's
  11 years **only 2016–2019 is priceable** — **6,390 of 14,727 events at k = 2.5** (§1c).
* The **EOD chain freeze carries 8 expiries per date at DTE 3–59** and *"nothing at 150–210 at
  all"* (`O-1`), so a long-tenor cell needs the **pinned harvest freeze**.
* **Tier E reaches 200–858 DTE for 2016–2018 ONLY** (`SC-3`), and that window is a near-zero-`rf`
  regime.
* `O-1` measured the harvest freeze at **5.89% of panel cells**; tier coverage is **unmeasured**.

**KILL `K1`: per-(year × tenor × strike) cell coverage must be ≥ 0.30 of that cell's step-1 events,
and every cell below it is reported NOT RUN rather than pooled upward.** `O-1`'s own register
claimed *"~75% chain coverage"* and was **~17× wrong** because it applied an **alert-book** figure
to the **panel** — so coverage is measured on **this arm's own events**.

### 4b. The grid, fixed here

| axis | values | why these |
|---|---|---|
| tenor **Y** | **60–90 DTE**, **150–210 DTE** | 60–90 is where `DEEPITM-FIN` measured financing and where the harvest freeze is densest; 150–210 is Don's *"enough time to expiry"* and is **conditional on `K1`** |
| strike **Z** | **0.70 delta ITM**, **ATM**, **5% OTM** | three points, no sweep |
| holding period | **the horizon step 1 passed on**, and only that one | choosing it afterwards is choosing the cell on the outcome |

**MONEYNESS IS FIXED ALONGSIDE DELTA, DELIBERATELY.** `V6-OPT`'s mechanism finding was that a
delta-targeted rule *"neutralises the very risk difference the trade was built to exploit"* —
because after a drop implied volatility jumps, so a fixed delta moves the strike. Fixing **both**
is what stops that recurrence, and the register reports the realised moneyness **and** delta of
every cell so the two cannot drift apart unnoticed.

### 4c. THE HURDLE IS THE IMPLIED-VOLATILITY JUMP, AND IT IS THE WHOLE QUESTION

**Implied volatility rises after a sharp drop, so the call costs more exactly when this strategy
buys it.** The bounce must beat what the option price already assumes — and the record has the
instrument: `V6-OPT` stage 1 measured post-dip `atm_iv_30` at **+17.71%** above the name's own
trailing 252-day median for healthy dips and **+13.29%** for unhealthy, *"so the market does NOT
price the `M1` distinction"*, with the elevation decaying **−16.56% by t+30**.

**So step 2 reports three things and a pass requires all three:**
1. the call's realised return beats **random-day entry on the same names** (`R2`'s method);
2. it beats **simply buying the shares** over the same horizon — because if the stock bounce is the
   whole effect, a call adds cost and leverage and nothing else;
3. the **IV decomposition**: how much of the return is the move, how much is IV mean-reversion, and
   how much is paid away in theta and spread. **A pass carried entirely by IV mean-reversion is a
   short-volatility trade in a call's clothing and must be labelled one.**

### 4d. Costs, charged not assumed

Full quoted spread through the **shipped fill engine** (`options_fill.round_trip`), `O10`/`O18`'s
**ρ = 0.6743** reported beside it and **labelled an extrapolation**, the **split guard passed
explicitly**, and `SC-3`'s financing figures charged for the long-tenor cell. **And `O-1`'s
reported defect is avoided by construction:** `market_tail.tail_mass_row` indexes a hard-coded
`PRIMARY_THRESHOLD` and raises for any caller whose thresholds omit 0.70, so step 2 drops to the
shipped primitives (`pick_expiry` + `rnd.build_slice`) rather than calling it.

---

## 5. STEP 3 — FORWARD PAPER BOOK *(only if step 2 passes)*

On the **`S3-I1` fleet harness**, declared **before any fill**, with `O11` governing: the
declaration committed ALONE, the entry rule frozen, `O11`'s text **verbatim or refused**, and the
seven-field verdict horizon filled field by field. **A delta-targeted strike is REFUSED unless the
declaration argues past `V6-OPT`'s autopsy** — which this program must do explicitly, since §4b's
grid is partly delta-defined.

**`O11` IS THE REASON STEP 3 EXISTS RATHER THAN STEP 2 BEING THE END.** A +3.27%/trade book ended
**−25.9%** at cap 10. **And dip events cluster by construction (§1a), so the concurrency problem is
structurally worse here than for the alert book**: `O11` measured 51.5% of trades falling in weeks
of more than ten alerts and expectancy of **−4.51% in quiet weeks against +14.28% in the top
decile**. **Step 3 reports survivability at `O11`'s own caps, never expectancy alone.**

---

## 6. PROVENANCE — `DC-1`'s BINDING NOTE, HONOURED

`DC-1` recorded that its mechanism *"was generated from two names Don holds, both of which
recovered — selection on the outcome three times over"*, and left two pre-commitments that **bind
any successor**. Both are carried:

1. **If the panel is extended past 2026-01-28, `NOW` and `CRM` are EXCLUDED BY NAME and the
   exclusion is reported.** The build quadrant ends 2019 so this does not bite today; it is written
   down so it is not lost.
2. **A positive result is FIRST evidence, never confirmation.** The hypothesis originates in
   observed recoveries, so step 1 passing is a reason to run step 2 — not a reason to believe.

**AND THE SAME HAZARD IN THIS PROGRAM'S OWN FRAMING:** *"such companies recover"* is an observation
about companies that **did**. The tier is defined on `cap >= $10B` **at the event date**, never on
survival to today, and `E-5`'s terminal-value rule (§3d) keeps the ones that did not recover in the
sample.

---

## 7. TRIALS, THE GRID, AND BENJAMINI-HOCHBERG

**The prompt asks that the full grid be fixed and every cell counted as a trial.** The full grid is
fixed in §3 and §4. On counting, here is the arithmetic and then a recommendation:

| design | cells | equity/options `N` | hurdle | BH smallest threshold |
|---|---|---|---|---|
| **recommended**: 4 primary step-1 + 6 step-2 | **10** | eq 274→278, opt 310→316 | 3.3550 / 3.3938 | **0.01000** |
| every cell of the full surface | 144 | eq 274→418 | 3.4743 | **0.00069** |

**THE RECOMMENDATION IS 10 TRIALS, AND THE REASON IS THAT IT ACHIEVES THE INSTRUCTION'S PURPOSE AT
A FRACTION OF ITS COST.** The purpose of counting every cell is to stop a cell being chosen after
the fact. **A pre-fixed primary plus a surface that explicitly carries NO VERDICT achieves exactly
that** — it is how `E-5`, `V6` and `MA28-CARD` all handled sensitivities — while counting all 144
would push the smallest BH threshold to **0.00069** and raise the hurdle for every future equity
claim. **`MA6` holds that overstating `N` is the safe direction, so if the manager prefers the full
count the arithmetic above is the price and the design does not otherwise change.**

* **Step 1 = 4 equity trials:** 2 news arms × 2 primary horizons (5, 21).
* **Step 2 = 6 options trials:** tenor × strike, on the single surviving horizon.
* **Two hurdles apply and must not be mixed:** step 1 is **equity**, step 2 is **options**.
* **BH at q = 0.10 across the batch, `k` = 10**, membership fixed here; **a cell that cannot be
  built is NOT RUN and `k` stays 10** (shrinking it makes every surviving threshold easier).
* **Sensitivities carrying NO verdict**, fixed now: k ∈ {2.0, 3.0}; windows of 3 and 5 sessions;
  horizons 63 and 126; the quality/health overlay; `V6-B`'s health floors.

---

## 8. FOR DON — in plain words

**What would count as success.** Three things in order, and each can stop the program.

1. **The stock bounces by more than it costs to trade.** Concretely: after a −2.5σ day, a $10bn
   name beats both its own normal return **and** the market over the next month by enough to
   survive costs, **in both halves of 2009–2019**, and it holds when news-driven and no-news drops
   are separated. If the bounce is smaller than costs, **no call can rescue it** and we stop.
2. **A call captures more of that bounce than the shares do.** It has to beat buying the stock and
   beat buying the same call on a random day — because implied volatility jumps after a drop, so
   we are buying the option at its most expensive.
3. **A real book survives it.** A per-trade edge is not money: we already measured a
   positive-expectancy options book ending **25.9% down** on a $50,000 account, and dip events
   arrive in clusters, which makes that problem worse here, not better.

**The realistic odds, given what the record already says.** I would put step 1 at roughly
**25–30%**, and step 1-and-2 together at **10–15%**. The reasons are specific:

* The project's own best estimate of a dip effect is **+0.52% over three months** — and at that
  size this design **cannot see it**. The program only works if a sharp one-day drop behaves
  differently from a slow drawdown, which is plausible (the reversal literature says so) but is
  not something this record has established.
* Four related attempts have already failed: dips (`V6`), dip confirmation (`DC-1`), puts on dips
  (`V6-OPT`), and the live alert itself (`R2`, which **loses** to random entry).
* The one thing genuinely in our favour is **power**: there are **14,727** of these events against
  `DC-1`'s 400, and they are **not** concentrated in a few crash days — the worst single day holds
  only 2.4% of them. **So for the first time in this family we can get a clean answer rather than a
  shrug.** A clean "no" is worth having.

**Roughly how long each step takes.** Step 1 is **cheap** — equity prices we already hold, no new
data, and the event census above already ran in minutes; the register and arms are a session or
two. Step 2 is **slower and narrower**: options only exist from 2016, so it runs on **4 of the 11
years** and about 6,400 events before coverage is counted, and it needs the harvest freeze. Step 3
is **months of calendar time** by construction, and it is the only one that produces evidence about
money rather than about a number.

**What I would not do.** I would not condition the headline on the quality score. The composite
does not sort the optionable universe before 2021, and the health floors already did **no work** on
a near-identical dip population. "Rock solid" is carried by the **$10bn tier** in the primary, and
the score is read as a sensitivity only.

---

## 9. WHAT THIS DRAFT DOES NOT DO

* **No register committed, no arm run, no option priced, no trial booked.** §1's census is a
  feasibility count that touches **no forward return** and can only block.
* **No Stage-2 look and no check-quadrant look.** 2020–2026 × the other ticker half stays closed;
  using it to choose among these cells would spend it with no replacement. **2020 and 2022 — the
  two most interesting dip years — are IN the check quadrant and are therefore NOT available to
  step 1**, which is a real cost and is stated rather than discovered.
* **The 1999–2008 proxy is not read**, and if it ever is, charter §5 binds: five themes, an
  increment only, never a validation of the shipped seven-theme construction.
* **The 1972–1998 WRDS era stays closed** — `OOS1`'s Gate B reads **0.837303** against **0.90**.
* **No X7 or `CORRECTED-FLOORS` floor is quoted as a bar for a daily event study**; those are
  calibrated on quarterly decile books, and every critical value here is **LABELLED UNCALIBRATED**.
* **Nothing is adopted and no trade is placed.** Adoption is Don's, is a vintage event, and quotes
  the expected return at **half** the backtested size (McLean-Pontiff).
* **The 63-session SD of 20pp in §1b is an ANCHOR, not a measurement** — the register measures it
  before fixing any bar.
