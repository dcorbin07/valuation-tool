# PREREG — DIP-CALL — calls after a sharp drop in a strong, liquid company

**THIS IS THE REGISTER. It is committed ALONE (markdown only, zero `.py`) and is a strict git
ancestor of every commit that computes an outcome** — `RESEARCH_CHARTER.md` §3. Nothing below is
edited after an outcome exists; corrections are reported beside it (`MB1`'s discipline).

**Authorised by Don, `DECISIONS.md` 2026-10-08:** *"calls after a sharp drop in a strong, liquid
company is authorised as a research program — stock-level bounce first, the option expression only
if the bounce survives, then a forward paper book. Same discipline as all research; no real
trades."*

**EXECUTOR PASS ON `PREREG_DRAFT_dipcall.md` (scout, commit `9850768`) AND ITS CENSUS (`6b338b5`,
`data/free_analysis/DIPCALL_CENSUS.json`). THE DRAFT IS ACCEPTED IN SUBSTANCE AND AMENDED IN
TWELVE PLACES, EVERY ONE BEFORE ANY OUTCOME EXISTS.** §0 states the amendments and why. The
draft's structure, its power analysis, its §2 not-a-re-run table, its §6 provenance commitments
and its §8 plain-words framing are adopted as written and are not restated here.

**NOTHING IS ADOPTED. NO REAL TRADE IS PLACED, EVER.** Adoption is Don's and is a vintage event.

---

## 0. EXECUTOR AMENDMENTS — twelve, all pre-outcome, and three of them are tightenings

**None of these relaxes a bar.** `W-28`'s rule — a pre-committed bar may never be relaxed after
watching it fail — binds this register from the moment it is committed, and A3 and A4 raise bars
the draft left absent or unfireable.

### A1 — THE NEWS WINDOW WAS UNSPECIFIED, AND THE SPLIT IS UNDEFINED WITHOUT IT
The draft's §3b makes the news/no-news split *"two arms and never one"* and never says what makes
an event news-dated. **Earnings are released after the close or before the open, so the price
reaction is the announcement session or the one immediately after it.** FIXED: an event at the
name's own session index *i* is **NEWS** iff a code-22 announcement falls at session index *j*
with **i − j ∈ {0, 1}**, measured in the name's own trading sessions, never in calendar days — a
Friday-after-the-close announcement reacts on Monday, which is three calendar days later and one
session later. Everything else on a name with KNOWN coverage is **NO-NEWS**. A name with UNKNOWN
coverage is neither (A1b).

**A1b — UNKNOWN IS A THIRD STATE AND IS EXCLUDED BY NAME, NEVER READ AS "NO NEWS".** `O6`/`O7`
measured **29 of 186 names as foreign private issuers with ZERO earnings dates**, so a filter
reading "no date" as "no announcement" fails OPEN on a non-random tenth of the book. The dates come
from the shipped `valuation/edge/event_spine.EventSpine` — **called, never re-implemented** (`B7`)
— whose `dates_or_unknown` returns `None` for a name with no coverage anywhere. Those names are
**counted, listed by name in the artifact, and dropped from both arms.**

### A2 — A BRACKET IS NOT AN INFERENCE: THE SE IS CLUSTERED, TWO WAYS, AND BOTH MUST CLEAR
The draft's §1a reports the effective-n honestly as a **bracket** [distinct event days, raw count]
and its §3d leaves the bar as *"the arm's own within-date permutation p95"*. A bracket cannot
produce a *t*. FIXED, and it is a **tightening**: every arm's *t* is computed **three** ways and
must clear its bar under **ALL THREE**:

1. **DATE-CLUSTERED** — clusters are event dates. This is the unit §1a's census identified: a
   market-wide drop creates thousands of simultaneous events sharing one shock.
2. **NAME-CLUSTERED** — clusters are tickers. Date-clustering does **not** absorb the *other*
   dependence in this design: **one name can have two events a few sessions apart and a 21-session
   window overlaps itself.** `R9` measured lag-1 autocorrelation of **+0.189** on this project's
   own spread and made the HAC *t* the number quoted; the same hazard here runs through a name, not
   through a date, and no date-clustered SE can see it.
3. **THE ARM'S OWN WITHIN-DATE PERMUTATION p95** — the event flag shuffled across names within
   each date, 500 draws, preserving each date's event count exactly. Calibrates the bar on this
   design rather than borrowing one.

**EVERY CRITICAL VALUE IN THIS REGISTER IS LABELLED UNCALIBRATED.** `V2G` established and
`R1-VAR` re-confirmed that no calibrated floor exists for a paired within-panel difference, and
`CORRECTED-FLOORS`' seven floors are calibrated on **quarterly decile books**, not on a daily
event study. No X7 floor is quoted anywhere.

### A3 — KILL `K4` COULD NOT FIRE AS WRITTEN, AND A KILL THAT CANNOT FIRE IS NOT A KILL
The draft's kill 4 bars *"mean per-date |ρ| between the event flag and the name's own trailing
volatility rank"* at **0.30**. At k = 2.5 the census measures **7.06 events per event day** across
a tier of several hundred names, so that is a point-biserial correlation between a flag that is 1
on roughly **1.5% of a date's rows** and a rank: it is small **by construction**, and the bar can
barely be reached whatever the truth is. This project has paid for this shape four times
(`W-1`'s hook guard walked through by `or True`, `S3-I3`'s banned NAME against an inline
re-derivation, `MB16`'s kill statistic structurally blind to the renaming it existed to catch,
`MB15`'s gate that 60.4% of arbitrary mappings passed).

**FIXED by ADDING a second, discriminating form. The kill fires if EITHER exceeds:**
* the registered **|ρ| ≥ 0.30**, unchanged; **and**
* the **event rate in the top trailing-volatility quintile ≥ 3.0× the rate in the bottom
  quintile**, measured on all scoreable name-days.

**3.0× is pre-committed and LABELLED UNCALIBRATED, and it is deliberately generous.** Under a
Gaussian null with a perfectly estimated scale the ratio is 1.0; fat tails and volatility-of-
volatility can lift it without the event being a volatility sort, whereas a genuine volatility
sort puts essentially every event in the top quintile and reads in the **tens**. A bar set tight
enough to kill a legitimate arm is the error `W-1`'s `K2` made — its 5% bar was taken from the
wrong population and *"would have killed a legitimate arm"*. **The full five-quintile event-rate
profile ships either way**, pass or fail.

### A4 — THE ECONOMIC FLOOR IS PRE-COMMITTED AT +0.67pp; THE DRAFT HAD NO NUMBER
§8 asks that the bounce beat *"enough to survive costs"* and never fixes the figure. FIXED:
**the point estimate must be ≥ +0.67pp**, which is **2 × `B11`'s MEASURED 33.4 bps one-way**
realised cost. **LABELLED AN EXTRAPOLATION**: `B11` measured that on the 2,531-name decile book,
and a $10B tier is cheaper to trade — so borrowing it **overstates** the cost and the error runs
toward failing, which is the safe direction (`MA6`).

### A5 — THE PASS RULE IS PER-ARM AND THE ADVANCING ARM IS NAMED
The draft runs news and no-news *"separately, never pooled"* and never says what a program pass is
when one passes and one does not. **Requiring both would require the literature the split is built
on to be wrong**: Chan (2003) predicts no-news shocks **reverse** and Savor (2012) predicts
information shocks **drift**, i.e. opposite signs. FIXED: **each of the four step-1 arms carries
its own verdict; step 2 runs on an arm that satisfies every condition of §2f in both halves, and
that arm is NAMED in the verdict.** Multiplicity is handled by BH over a batch whose membership is
fixed here, which is what makes this not a cherry-pick.

### A6 — THE BH p IS TWO-SIDED; THE PASS ALSO REQUIRES A POSITIVE SIGN
Because A5's two arms have **opposite predicted signs**, no uniform one-sided direction can be
declared. FIXED: the *p* entered into BH is **two-sided** (which costs power and is honest), while
the **pass additionally requires the point estimate to be POSITIVE** — a negative drift is not a
bounce and cannot support buying a call. Both conditions are stated now so neither can be chosen
afterwards.

### A7 — TRIAL TIMING: 4 EQUITY NOW, 6 OPTIONS AT THE MOMENT STEP 2 IS AUTHORISED; **BH `k` STAYS 10**
Step 1 runs for certain, so its **4 equity trials are booked before any runner exists**. Step 2's
**6 options trials are booked the moment step 1's verdict authorises step 2 and BEFORE any option
price is read** — also before its runner exists. Charging the options lane 6 trials for a search
that may never happen would raise every future options hurdle for nothing (`MB1-SEL`, `MB3`,
`MB15`, `W-14` and `DC-1` all logged **zero** for arms that never ran). **`k` = 10 for BH either
way**: if step 1 fails the true batch is 4, and `k` = 10 makes every surviving threshold **harder**
(*i*·0.10/10 < *i*·0.10/4), which is the safe direction. The membership is fixed in §7 and is not
reopened.

### A8 — THE MARKET LEG IS BUILT FROM HALF-0 NAMES ONLY, INSIDE THE BUILD YEARS
The draft's §3d wants *"the panel's own value-weighted return, built from panel prices"*. Built
from **all** names that would read 2009–2019 × **half 1** — a *different* cell of §4's 2×2, and
the charter's budget is one build cell and one check cell. FIXED: the market return is the
**cap-weighted daily return of half-0 panel names with price files, 2009–2019 only**, weights from
the **most recent prior quarterly `market_cap`** (point-in-time, no look-ahead). **`X1` is what
licenses this**: halving the universe moved the centre of 200 half-books not at all (median
+0.07233 against the full universe's +0.07174), so a half-0 market is a sound proxy rather than a
convenience. Ken French is used **nowhere**.

### A9 — ENTRY TIMING AND THE HORIZON WINDOW, WHICH THE DRAFT NEVER FIXED
The event is defined by day *t*'s return, which is known only at day *t*'s close. FIXED: **entry
at the close of session *t*; the horizon return runs over sessions *t*+1 … *t*+*h***, and the
market and own-normal legs are measured over **exactly that window**. The volatility scale is
already strictly prior (`shift(1)`), so nothing in the event definition sees its own day.

### A10 — THE 63-SESSION SD IS MEASURED BEFORE ANY BAR IS FIXED
The draft's own words: *"the 63-session SD of 20pp in §1b is an ANCHOR, not a measurement."*
Executed: §1's power table is **re-derived from the SD measured on the arm's own rows** in the
free-kill pass, before any outcome statistic is read, and both the anchored and measured tables
ship.

### A11 — `E-5`'s TWO CENSORING CAUSES ARE SEPARATED IN CODE, NOT ASSERTED
A name whose price series ends inside the horizon is **TERMINAL** — booked at
`last_close / c0 − 1` — iff `ACTIONS` records `delisted`, `bankruptcyliquidation`,
`regulatorydelisting`, `voluntarydelisting`, `acquisitionby` or `mergerto` at or after the last
price. Otherwise it is an **ADMINISTRATIVE** censor: the row is **DROPPED and COUNTED**, never
booked at a short-window return. `E-5` measured the cost of conflating them — **591 rows whose
ticker stops trading inside the window silently deleted 16 crashes, 5 of them flagged** — and
verified the terminal rule reproduces the panel's own `fwd_ret` at max |Δ| **0.000e+00** on 591 of
591. Both counts ship.

### A12 — TIER MEMBERSHIP IS POINT-IN-TIME, NOT "EVER IN THE TIER"
The census's **459** names are *"ever `market_cap >= $10B` on a build-quadrant date"*, which
counts a name's 2009 events because it reached $10B in 2019 — selection on a future property, and
the draft's own §6 forbids it (*"the tier is defined on `cap >= $10B` **at the event date**, never
on survival to today"*). FIXED: an event qualifies iff the name's **most recent prior quarterly
panel `market_cap` is ≥ $10B**. The census's 459 is a **feasibility upper bound**; the arm's own
count will be lower and **the per-date tier name count ships**, as `RESEARCH_CHARTER.md` §5
Stage 1b requires, together with whether the tier clears `CONTRACT_MIN_POSITIONS` = **50** on
every date.

---

## 1. POWER, AND THE HURDLE DERIVED NOT QUOTED

`statistics.hlz_hurdle` is **called**, never retyped (`MA5`: the "3.0" constant was √(2·ln N)
frozen at N = 90). At the stamp committed with this register the hurdle is **re-read from
`research_log.detail()` after merging `origin/main`** and is recorded in the artifact, not here —
r1 is booking equity trials concurrently and any figure typed into this file rots within days
(`MA37`, `MB32`).

**`MB22`'s gate: the 80%-power MDE is `(crit + 0.84) · se`, NOT `crit · se`.** Every MDE this
project published before `MB22` was a 50%-power figure. **Both** are reported, from
`power_gate.state(effect, se, n_trials=...)` so the arithmetic is not retyped
(`RUN_RULES` PART A rule 11).

**PRIMARY HORIZONS: 21 sessions and 5 sessions, co-primary.** 63 and 126 are **sensitivities
carrying NO verdict**, and the reason is stated before the run: the draft's §1c shows power dies
there, and they are exactly where `V6` and `DC-1` already looked. **The record's own banked dip
effect is +0.5203pp over 63 days (`V6`'s A3, via `DC-1`) and needs ~28,097 events — NOT REACHABLE
at any k.** A null at 63 or 126 sessions is therefore **uninformative by construction** and may
not be quoted as a result.

---

## 2. STEP 1 — DOES THE STOCK BOUNCE?

### 2a. The event
`r_t ≤ −k · σ_{t−1}`, σ = trailing **60-session** SD of daily returns taken **strictly before**
the event day (`shift(1)`), **40-observation** minimum. **PRIMARY k = 2.5, one-session window.**

**VOLATILITY-RELATIVE IS THE POINT.** A flat percentage would make the event a volatility sort
wearing a dip's name — `V6`'s inverse-momentum finding (Spearman(drawdown, `momentum`) =
**+0.6642**) waiting to recur. `A3`'s kill is what checks it rather than assuming it.

**THE PRICE BASIS: SPLIT- AND DIVIDEND-ADJUSTED FOR THE EVENT, RAW FOR ANY STRIKE.** `V6`'s `C5`
pinned both sides — on a raw series a 2-for-1 split reads as a −50% drawdown, and companies split
**after** they rise, so a raw basis flags the strongest names in the universe — and `O-1` paid the
other half when **MNST's 3-for-1 booked a fake +1453%**. Consistent with `DECISIONS.md`
2026-10-08, which puts the dip detector's own 52-week high on the adjusted basis.

### 2b. Population — BOTH, AND THE TIER GOVERNS (`RESEARCH_CHARTER.md` §5 Stage 1b)
* **FULL corrected universe, half 0** — *is the signal real?*
* **THE $10B TIER, POINT-IN-TIME (A12)** — *is it any use to us?* **THIS READING GOVERNS
  ADVANCEMENT.**
* An arm passing wide and failing the tier is **`REAL BUT NOT INVESTABLE HERE`** and does **NOT**
  advance to step 2. A disagreement between the two is a reported finding, not a nuisance.

### 2c. Statistic
Mean abnormal return over the horizon, abnormal measured **two ways, BOTH reported, and quoting
one alone is FORBIDDEN** — `DC-1` measured these disagreeing in sign (**+0.5203pp** own-normal
against **−0.1200pp** vs-universe):
* **own-normal**: `r_i(t+1…t+h) − h × mean daily return of name i over the same strictly-prior
  60-session window`;
* **market**: `r_i(t+1…t+h) − r_m(t+1…t+h)`, `r_m` per **A8**.

A pass requires the condition in §2f under **both** definitions.

### 2d. Both halves, inside the build quadrant
**2009–2014 / 2015–2019, boundary EMBARGOED**: an event whose horizon window crosses 2015-01-01
is dropped from both halves and **counted**. An arm clearing one half is **`NOT_REPLICATED`** and
does not reach step 2.

### 2e. NO SURVIVOR FILTERING — per **A11**.

### 2f. THE PASS CONDITION, fixed here as a CONJUNCTION
An arm passes iff **all** of:
1. point estimate **POSITIVE** (A6);
2. point estimate **≥ +0.67pp** (A4);
3. clears its own within-date permutation p95 **and** |*t*| > the derived hurdle under **BOTH**
   clustering readings (A2);
4. in **BOTH** halves (2d), with the same sign;
5. under **BOTH** abnormal-return definitions (2c);
6. on the **$10B tier** (2b);
7. its two-sided *p* survives **BH at q = 0.10, k = 10** (§7).

**Ambiguous against any of these is a NULL, not a judgement call** (`RUN_RULES` PART A rule 6).

### 2g. FREE PRE-OUTCOME KILLS — run in their OWN PASS, read before any arm
`RESEARCH_CHARTER.md` §7, and `O10`'s process defect is not repeated: the kill pass is a separate
invocation, its artifact is written first, and **the arm runner REFUSES to run without a passing
kill artifact**.

1. **EVENT COUNT ≥ 1,500** in **each** news arm in **each** half, on the arm's own rows.
   **THE DRAFT'S OWN DISCLOSURE IS CARRIED, NOT HIDDEN: the 1,500 was written with §1a's census in
   view.** Two things bound it, and a stricter reader may still discount it. **(a) It is DERIVED
   from the power table**, sitting between the 585 needed for +2.0pp and the 2,341 needed for
   +1.0pp at the primary 21-session horizon. **(b) An event COUNT is not an OUTCOME** — nothing in
   the census reads a forward return, so knowing how many events exist cannot indicate which way
   an arm will go. **This register may raise the floor and may never lower it** (`W-28`).
2. **EARNINGS COVERAGE ≥ 0.70** of tier names, UNKNOWN names counted and excluded by name (A1b).
3. **THE DESIGN EFFECT MEASURED AGAINST ITS OWN SHUFFLED NULL**, via the shipped
   `options_stats.effective_n` — **called, never re-implemented**. `R3` established that **a raw
   design effect is not evidence of clustering**: 600 independent draws in 12 blocks returned a
   design effect near 1.8 from sampling error alone, and applying it as a haircut *"would have
   manufactured a correction out of noise."* The effective-n **bracket** is reported, never either
   end alone.
4. **THE EVENT MUST NOT BE A VOLATILITY SORT** — **per A3, fires if EITHER form exceeds.**
5. **THE 63-SESSION SD IS MEASURED** and the power table re-derived from it (A10).

**A kill firing stops the program at zero further trials and is the cheapest good outcome
available to it** (`DC-1`'s own words).

---

## 3. STEP 2 — IS A CALL THE RIGHT WAY TO OWN IT? *(only if §2f passes)*

**Adopted from the draft's §4 unchanged**, with the trial timing of **A7**.

### 3a. COVERAGE IS CENSUSED FIRST, BEFORE ANY PRICE IS READ
Stated before any number: the derived options layer spans **2016-01-04 → 2025-12-31** (`U2`), so
only **2016–2019** of the build quadrant is priceable; the EOD chain freeze carries **8 expiries
per date at DTE 3–59** and *"nothing at 150–210 at all"* (`O-1`); **Tier E reaches 200–858 DTE for
2016–2018 ONLY** (`SC-3`), a near-zero-`rf` regime; `O-1` measured the harvest freeze at **5.89%
of panel cells** and tier coverage is **UNMEASURED**.

**KILL `K1`: per-(year × tenor × strike) cell coverage ≥ 0.30 of that cell's step-1 events. Every
cell below it is reported NOT RUN and is never pooled upward.** `O-1`'s own register claimed
*"~75% chain coverage"* and was **~17× wrong** because it applied an **alert-book** figure to the
**panel**, so coverage is measured on **this arm's own events**. **Chain coverage ships by year AND
by tenor before any option figure is read**, as the prompt requires.

### 3b. The grid, fixed here — no sweep
| axis | values | why |
|---|---|---|
| tenor | **60–90 DTE**, **150–210 DTE** | 60–90 is where `DEEPITM-FIN` measured financing and where the freeze is densest; 150–210 is Don's *"enough time to expiry"* and is **conditional on `K1`** |
| strike | **0.70-delta ITM**, **ATM**, **5% OTM** | three points |
| holding period | **the horizon step 1 passed on, and only that one** | choosing it afterwards is choosing the cell on the outcome |

**MONEYNESS IS FIXED ALONGSIDE DELTA, DELIBERATELY.** `V6-OPT`'s mechanism finding was that a
delta-targeted rule *"neutralises the very risk difference the trade was built to exploit"*,
because implied volatility jumps after a drop and a fixed delta moves the strike. Fixing **both**
is what stops the recurrence, and **the realised moneyness AND delta of every cell ship** so the
two cannot drift apart unnoticed.

### 3c. THE HURDLE IS THE IMPLIED-VOLATILITY JUMP, AND A PASS REQUIRES ALL THREE
`V6-OPT` stage 1 measured post-dip `atm_iv_30` at **+17.71%** above the name's own trailing
252-day median for healthy dips and **+13.29%** for unhealthy — *"so the market does NOT price the
`M1` distinction"* — decaying **−16.56% by t+30**. So the call costs more exactly when this
strategy buys it, and:
1. it beats **random-day entry on the same names** (`R2`'s method, which `R2` used to kill the live
   alert at **−5.0640pp**);
2. it beats **simply buying the shares** over the same horizon — if the stock bounce is the whole
   effect, a call adds cost and leverage and nothing else;
3. the **IV decomposition** ships: how much is the move, how much is IV mean-reversion, how much is
   paid in theta and spread. **A pass carried entirely by IV mean-reversion is a short-volatility
   trade in a call's clothing and must be LABELLED one.**

### 3d. Costs, charged not assumed
**Full quoted spread through the shipped `options_fill.round_trip`**, with `O10`/`O18`'s
**ρ = 0.6743** [0.6617, 0.6871] reported beside it and **LABELLED AN EXTRAPOLATION** (ρ was
measured on 35-delta ~60-DTE calls). **THE SPLIT GUARD IS PASSED EXPLICITLY** — `simulate_trade`'s
`splits=` **defaults to `None`**, and `O-1`'s portable lesson is that *"a guard whose default is
OFF for backward compatibility is a guard a new caller silently loses."* `SC-3`'s financing figures
are **charged** for the long-tenor cell and **not re-derived** (`MB4`: *"nobody should spend a
trial re-deriving this"*). **`market_tail.tail_mass_row` is NOT called** — `O-1` reported that it
indexes a hard-coded `PRIMARY_THRESHOLD = 0.70` and raises for any caller omitting it — so step 2
drops to the shipped primitives (`pick_expiry` + `rnd.build_slice`).

---

## 4. STEP 3 — FORWARD PAPER BOOK *(only if step 2 passes)*
On the **`S3-I1` fleet harness**, declaration committed **ALONE** before any fill, entry rule
frozen, `O11`'s text **verbatim or refused**, the seven-field verdict horizon filled field by
field, and **a delta-targeted strike REFUSED unless the declaration argues past `V6-OPT`'s
autopsy** — which this program must do explicitly, since §3b's grid is partly delta-defined.

**`O11` IS WHY STEP 2 IS NOT THE END.** A **+3.27%/trade positive-expectancy** book ended at
**$37,059 from $50,000** at cap 10, with expectancy **−4.51% in quiet weeks against +14.28%** in
the top decile and **51.5%** of trades in weeks of more than ten alerts. **Dip events cluster by
construction**, so the concurrency problem is **structurally worse here than for the alert book.**
**Step 3 reports survivability at `O11`'s own caps, never expectancy alone.**

---

## 5. PROVENANCE — `DC-1`'s BINDING NOTE, CARRIED
`DC-1` recorded that its mechanism *"was generated from two names Don holds, both of which
recovered — selection on the outcome three times over"*. Both of its pre-commitments bind here:
1. **If the panel is extended past 2026-01-28, `NOW` and `CRM` are EXCLUDED BY NAME and the
   exclusion is reported.** The build quadrant ends 2019, so this does not bite today; it is
   written down so it is not lost.
2. **A positive result is FIRST evidence, never confirmation.**

**AND THE SAME HAZARD IN THIS PROGRAM'S OWN FRAMING:** *"such companies recover"* is an
observation about companies that **did**. **A12** defines the tier at the event date and **A11**
keeps the ones that did not recover in the sample.

---

## 6. VOID CONDITIONS
1. Quoting a 63- or 126-session reading as a verdict (§1).
2. Quoting one abnormal-return definition without the other (§2c).
3. Quoting the wide-universe reading as a statement about the tier, or the reverse.
4. Relaxing any bar in §2f or §2g after seeing it fail (`W-28`).
5. Promoting a sensitivity cell (§7) to a verdict without its own later register.
6. Opening the **check quadrant** (2020–2026 × half 1) or the **1999–2008 proxy** anywhere in
   step 1. **2020 and 2022 — the two most interesting dip years — are IN the check quadrant and
   are therefore NOT available**, which is a real cost and is stated rather than discovered.
7. Quoting any X7 or `CORRECTED-FLOORS` floor as a bar for a daily event study.
8. Conditioning the step-1 headline on the quality/health score. `P1S0` found the composite does
   not sort the optionable universe before 2021 (H=63 early *t* **0.8352** against a floor of
   1.6974) and `V6-OPT` found the health floors **did no work** on a near-identical dip population
   (healthy **+1.1342%** against unhealthy **+1.2651%**). *"Rock solid"* is carried by the **$10B
   tier**; the score is a **labelled sensitivity carrying no verdict**.

---

## 7. TRIALS, THE BATCH, AND BENJAMINI-HOCHBERG

**THE BATCH MEMBERSHIP IS FIXED HERE AND IS NOT REOPENED** — choosing afterwards which arms were
"in the batch" is how BH is gamed.

* **Step 1 = 4 EQUITY trials:** 2 news arms × 2 primary horizons (5, 21).
* **Step 2 = 6 OPTIONS trials:** tenor (2) × strike (3), on the single surviving horizon.
* **`k` = 10, q = 0.10.** The *i*-th smallest *p* is compared against *i* · 0.10 / 10, so the
  smallest must beat **0.01000** and the largest **0.10**.
* **A cell that cannot be built is NOT RUN and `k` STAYS 10** — shrinking it makes every surviving
  threshold easier.
* **Two hurdles apply and must NOT be mixed:** step 1 is **equity**, step 2 is **options**.
* **Trial timing per A7.** **BH controls the false-discovery rate across the batch; it is not a
  licence to present a survivor as confirmed** — that is step 2's and step 3's job.

**SENSITIVITIES CARRYING NO VERDICT, FIXED NOW:** k ∈ {2.0, 3.0}; windows of 3 and 5 sessions;
horizons 63 and 126; the quality/health overlay; `V6-B`'s health floors; the six-theme
complete-case reading. **Every other cell of the full surface is a REPORTED SURFACE carrying NO
VERDICT and can only be promoted by its own later register.** The draft's §7 arithmetic for the
full 144-cell count is accepted: counting all of them would push the smallest BH threshold to
**0.00069** and raise the hurdle for every future equity claim, and **`MA6` holds that overstating
`N` is the safe direction**, so if Don or the manager prefers the full count the price is recorded
and the design does not otherwise change.

---

## 8. EXPECTATIONS, registered before any outcome exists
Scored honestly afterwards, right or wrong. The draft's §8 priors are adopted: **step 1 at roughly
25–30%**, **step 1 and 2 together at 10–15%**.

1. **No kill fires** — 60/40. The count floor is the one most at risk, because **A12**'s
   point-in-time tier is strictly smaller than the census's 459 "ever" names.
2. **The design effect IS measurable** against its own shuffled null — 70/30. The census's mild
   day-concentration (worst single day **2.35%** of events at k = 2.5) is about *concentration*,
   not about *within-day correlation*, and those are different quantities.
3. **The two abnormal-return definitions DISAGREE in magnitude by more than 2×** — 55/45, on
   `DC-1`'s precedent where they disagreed in **sign**.
4. **The no-news arm is the stronger of the two** — 60/40, following Chan (2003).
5. **At least one arm flips sign between halves** — 65/35. This is the record's most repeated
   pattern (session 7's LOO, `S17`, `V6`, `S8`/`S9`, `S11`/`S12`, `O21-D2`, `E-2`, `D6`, `MB20`).
6. **Step 1 fails** — 70/30, which is the draft's own prior stated the other way round.

---

## 9. WHAT THIS REGISTER DOES NOT DO
* **It does not adopt anything, and it places no trade, ever.**
* **It does not re-open `V6`, `V6-B`, `V6-OPT`, `DC-1`, `O17C4` or `R2`.** The draft's §2 table is
  the argument that this is a different question, and it is adopted rather than re-argued.
* **It does not read the check quadrant, the 1999–2008 proxy, or the 1972–1998 WRDS era**
  (`OOS1`'s Gate B reads **0.837303** against **0.90**, so that era stays closed).
* **It re-derives no landed figure** — `DEEPITM-FIN`'s 701.87 bps, `SC-3`'s four strata, `O10`'s ρ,
  `V6-OPT`'s IV elevation, `O11`'s caps and `B11`'s 33.4 bps are all **charged as inputs**, not
  re-measured.
* **It quotes no hard-coded trial count, hurdle or vintage** — all three are derived at run time
  (`MA5`, `MA37`, `MB32`).
