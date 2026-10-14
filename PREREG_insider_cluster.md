# PRE-REGISTRATION — `INSIDER-CLUSTER` — clustered opportunistic insider buying, in SHARES

**Committed ALONE, markdown only, zero `.py`.** This file must be a strict git ancestor of every
commit that computes an outcome. If it is not, the item is VOID.

Don's ruling, `DECISIONS.md` 2026-10-13 ("RESEARCH QUEUED"): *"clustered insider buying tested in
SHARES (F-15's options form is dead on arithmetic)."* The scout's `a8c1a75` computed why the call
cannot work — it needs **4.85% of premium at IV 0.30** against a published drift near **1.64% over
60 days**, short by **3.0×** — and recommended the stock side, where this project's own measured
equity cost (`B11`, **33.4 bps one way**) leaves 1.64% netting **+0.97%**.

**EVERY CONSTANT BELOW IS DERIVED FROM A PRE-OUTCOME CENSUS THAT RAN FIRST**
(`scripts/insider_cluster_census.py`, `insider_cluster_census2.py`;
`data/free_analysis/INSIDER_CLUSTER_CENSUS.json`, `INSIDER_CLUSTER_CENSUS2.json`). Those passes
read **no forward return, score nothing and compare nothing to a bar** — they answer only how many
events exist, how large the governing tier is and what dispersion the design faces, which are the
inputs a floor must come from. `O-1` is the precedent and the warning: it set a floor from an
alert-book coverage figure applied to the panel and was wrong by **~17×**.

---

## 1. The hypothesis, and its declared sign

**A cluster of OPPORTUNISTIC insider open-market purchases predicts a POSITIVE market-adjusted
return over the following `h` sessions.**

**SIGN: POSITIVE. Declared here, one-sided, before any outcome.** Cohen-Malloy-Pomorski (2012)
publish ~82 bps/month long-short for clustered opportunistic buying, and a two-sided reading taken
afterwards would be choosing the test on the result. This project has three times recorded a
published sign failing to reproduce (`O7`, `U2`, `MA31`), so a negative result is a finding about
the sign and not an invitation to flip it.

---

## 2. The construction — fixed before any outcome, implemented in `valuation/studies/insider_cluster.py`

1. **ROUTINE / OPPORTUNISTIC comes from `insider_routine.classify`** — CMP's published
   three-consecutive-year rule, **called and never re-implemented** (`B7`) — and is computed on the
   **FULL file**, because CMP classify an insider's habit from *any* trade and `MB20` measured that
   a truncated history **under-counts routine**.
2. **An open-market purchase is `transactioncode == "P"`. A row with a MISSING code is COUNTED AND
   SKIPPED** and never read as "not a purchase" (`MB20`'s correction).
3. **A CLUSTER EVENT is `k` or more DISTINCT `ownername` filing an opportunistic open-market
   purchase in the same ticker inside a 30-calendar-day window**, dated at the **LAST** filing in
   the window. `k = 2` **PRIMARY**; `k = 3` **SENSITIVITY, no verdict**.
4. **DATED ON `filingdate`, NOT `transactiondate`.** A Form 4 is not public until filed, and an
   event dated on the trade would read as if the market could see the filing before it existed. The
   ROUTINE habit is still measured in `transactiondate` months, because the habit is about when the
   insider TRADES — `insider_routine`'s own rule, unchanged.
5. **ONE EVENT PER CLUSTER**: the next event for a ticker needs its last filing strictly after the
   previous event date, so a busy quarter at one name cannot re-fire the same cluster.

### 2a. THE STRICT CONDITION, AND IT IS THE MOST CONSEQUENTIAL DECISION IN THIS REGISTER

**PRIMARY: the `(ticker, owner)` pair must have traded at least once in EACH of the two prior
calendar years**, so routine was *possible* and did not happen.

**Why, measured before any outcome existed.** `classify` labels a pair ROUTINE only on a
same-month repeat in both prior years, so **a pair with no prior years is OPPORTUNISTIC by
default** — not an insider breaking a habit, but an insider with no observable habit. On this
universe that is large, not marginal: **only 34.32% of the 589,322 opportunistic open-market
purchase rows have both prior years present, so 65.68% of the label is "no history to be routine
with"**. The corroborating figure is the routine share itself — **33.86% of classifiable rows on
the freeze's full file against `MB20`'s 60.47% under the identical rule on the narrower, older
`data/backtest` population**, which is exactly what a wider and younger universe produces.

**Without this condition the arm is a DATA-AVAILABILITY screen wearing a BEHAVIOURAL screen's
name — `S10`'s failure mode, and the one this project has repeated most.**

**The broad label is the declared SENSITIVITY**, named here so it cannot be reached for afterwards:
8,478 strict build-cell events against **25,304** broad ones, so the strict form costs **two thirds
of the sample** and is taken anyway.

### 2b. THE SOURCE IS THE FREEZE'S RAW SF2, AND THE EXPORT WOULD HAVE BEEN A DIFFERENT UNIVERSE

`sharadar_freeze._fresh_universe` ranks the TICKERS snapshot by **TODAY's `scalemarketcap`** and
keeps the top 3,000, so `data/backtest` is *the names that are biggest in 2026* — selection on a
present-day property, which is the charter's own reason for banning it as a panel. **Measured on
the insider file: the freeze carries 11,570,121 rows against the scout's 6,688,777 (1.73×) and
682,435 open-market purchase rows against 163,653 — 4.17×.** Scoring an insider signal on the
export would have selected the names by their own future size.

**A by-product, and it is why the skip rule is cheap:** the missing-code rows and the unclassifiable
rows are **the same rows** — 3,404,471 of 3,404,501 overlap, **99.999%**, with 30 code-missing-only
and 142 unclassifiable-only. Two holes quoted separately would have double-counted one hole.

---

## 3. The population — BOTH, and the tier governs (charter Stage 1b)

**BUILD QUADRANT: 2009–2019 × ticker half 0** (`X1`'s `sha1(ticker) % 2`), on the corrected full
raw universe panel (`UNIVERSE_BIAS_PANEL_full.pkl`). Both-halves boundary **2015-01-01**,
embargoed.

| population | events | ticker clusters | early / late |
|---|---|---|---|
| **FULL corrected universe** | **8,478** | 1,344 | 4,684 / 3,794 |
| **TIER, `cap >= $10B`** at the most recent PRIOR quarterly date | **215** | 79 | 66 / 149 |

The tier is 2.54% of the build cell. Its per-date name count ships with the result, as Stage 1b
requires.

---

## 4. The statistic

* **Mean abnormal return over sessions `t+1 … t+h`**, entry at the close of the event session,
  under **BOTH** definitions — **own-normal** (`h ×` the mean daily return over the same strictly
  prior 60-session window) and **vs the half-0 cap-weighted market** — and **quoting one alone is
  FORBIDDEN** (`DC-1` measured the two disagreeing). Both legs come from `dipcall_arm.abnormal`,
  **called, never re-implemented** (`B7`).
* **Cluster-robust standard errors on the EVENT DATE and on the TICKER, and clearing is required
  under BOTH.** Insider filings cluster in time (a market-wide window produces many at once) and in
  the cross-section (one name files repeatedly), and a design that absorbs only one of those is
  reporting the other as signal.
* **A within-date permutation null**: the event flag shuffled across names within each event date,
  **500 draws**, preserving each date's event count exactly (`dipcall_arm.permutation_null`).
* **Two-sided `p` from the clustered *t*** for the BH step, even though §1 declares a sign —
  `PREREG_dipcall2.md`'s rule, kept for its reason: taking the easier form in a successor, after a
  predecessor stopped, is the shape this project distrusts most.
* **A name whose series ends inside the horizon**: a DELISTED name has a **TERMINAL** value and is
  kept; an administrative end of data **CENSORS** and is dropped (`E-5`'s distinction, which cost
  that register a silent deletion of 16 crashes before it was separated). `terminal_names()` is
  the shipped rule.

---

## 5. The horizons — DERIVED, not chosen

CMP publish **~82 bps/month LONG-SHORT**. The long-only leg is **assumed to be half, 41
bps/month** — an **ASSUMPTION, labelled, used only to say what the design could see and never as
an expected return.** Drift accumulates as `h` while dispersion grows as `sqrt(h)`, so the
hypothesised effect at `h` sessions is `0.41pp × h/21` and the required `n` is proportional to
**1/h**.

| `h` | hypothesised effect | clears the **0.67pp** round-trip cost floor | required `n` at 80% power | full universe (8,478) |
|---|---|---|---|---|
| 5 | 0.10pp | **NO** | 32,729 | **NO** |
| 21 | 0.41pp | **NO** | 7,793 | yes |
| **63** | **1.23pp** | **YES** | **2,598** | **YES (3.3×)** |
| **126** | **2.46pp** | **YES** | **1,299** | **YES (6.5×)** |

**CO-PRIMARY: `h = 63` and `h = 126`** — the only two horizons whose hypothesised effect clears the
round-trip cost floor **and** whose required `n` is met. **SENSITIVITY, NO VERDICT: `h = 5` and
`h = 21`**, and the reason is structural rather than a preference: at those horizons the
hypothesised effect is **below the cost of trading it**, so they could not pass §6's clause A4 even
if the effect were exactly true, and reporting them as verdicts would be reporting a design's
arithmetic as a finding. (`DIP-CALL-3` reached the same pair of co-primaries independently, *"the
two that clear the cost floor"*.)

**A CORRECTION THIS REGISTER MADE AGAINST ITS OWN FIRST DERIVATION, before any outcome existed.**
The census's first pass compared **every** horizon against a flat 0.82pp, which is wrong in both
directions at once — it made `h = 126` look UNDERPOWERED (required `n` 11,689 against 8,478) and
`h = 5` look feasible. Scaling the effect with the horizon reverses both. It is recorded because
the error ran toward *declining a horizon that is in fact the best-powered one*.

---

## 6. The bars — all five required. Anything else is a NULL.

* **A1 — SIGN.** The point estimate is POSITIVE, under both return definitions.
* **A2 — ITS OWN NULL.** The mean exceeds that cell's own within-date permutation **p95**, on the
  full sample **and in both halves**, same sign throughout. **Halves disagreeing in sign is a NULL
  in either direction** — ten instruments in this record have shown that pattern.
* **A3 — INFERENCE.** The clustered *t* clears **2.0** under **both** clusterings.
  **LABELLED UNCALIBRATED** (`V2G`, `R1-VAR`): no X7 or `CORRECTED-FLOORS` figure transfers to an
  event-time mean on this universe, and none is quoted. The HLZ hurdle at the then-current equity
  `N` is **reported beside** every cell and is **not** gated, with `statistics.hlz_hurdle` derived
  rather than quoted.
* **A4 — ECONOMIC.** The point estimate exceeds **0.67pp**, a round trip at `B11`'s measured 33.4
  bps one way. `DIP-CALL`'s constant, reused verbatim rather than re-chosen.
* **A5 — BENJAMINI-HOCHBERG at q = 0.10 across the batch, `k = 2` FIXED HERE AND NEVER SHRUNK.**
  The batch is the two **assessable** cells: full universe × {63, 126}. **The two tier cells are
  EXCLUDED FROM THE BH SET and the exclusion is declared here with its reason** — §7's K1 fires on
  them before any outcome, so they carry no *p* to correct (charter Stage 1a's rule that an arm
  without a calibrated *p* is excluded *with the exclusion declared in the register*).

---

## 7. FREE PRE-OUTCOME KILLS — read in their own pass, BEFORE any arm

`O10`'s process defect: a gating control and its outcomes must not run in one pass. The arm runner
**REFUSES** without a passing kill artifact.

* **K1 — THE EVENT FLOOR, DERIVED.** A cell is assessable only if its event count reaches the
  required `n` of §5 at its own horizon. **ALREADY MEASURED, AND IT FIRES ON THE TIER AT EVERY
  HORIZON: 215 events against 2,598 required at `h = 63` and 1,299 at `h = 126`** — short by 12.1×
  and 6.0×. **So the governing population is `UNDERPOWERED-BY-CONSTRUCTION` and is declared so
  NOW, before any outcome**: power against the hypothesised effect is **7.2%** at `h = 63` and
  **10.0%** at `h = 126` on the clustered bound. **A tier null is therefore NOT a null** — it is
  *"invisible at this resolution"* — and it may not be reported as absence. Under charter Stage 1b
  an arm that cannot be assessed on the tier **does not advance to Stage 2**, so the check quadrant
  is not spent whatever the wide universe does. That is the cheapest honest outcome available and
  it is named in advance.
* **K2 — IS THIS `V6-B`'s DIP ARM AGAIN?** The share of cluster events that fall within 5 sessions
  of a `DIP-CALL` event (`z <= -2.5` on the shipped construction) must be **below 0.25**. `V6-B`'s
  arm 3 tested dip × insider buying and was **NULL**; if insider clusters mostly follow crashes,
  this register is re-running a failed arm under a new name. **Fires → the item stops.**
* **K3 — IS THIS THE `insider` THEME?** The mean per-date |Spearman| between the event flag and the
  `insider` theme z-score at the most recent prior panel date must be **below 0.60**. The theme's
  own IC *t* is **-0.24**; a flag that is mostly the theme inherits that and is not a new signal.
  The same 0.60 bar is read against **each** of the seven weighted themes, as `N6`/`N7`/`A11` did.
* **K4 — LOOK-AHEAD.** Zero events dated before their own filing date; the routine classification
  reads only strictly-prior years. Pinned by test with a **positive control**, so the guard cannot
  pass by refusing everything.

---

## 8. POWER — stated before the run (`RUN_RULES` PART A rule 11)

From the census's own dispersion bound (trailing 60-session SD × `sqrt(h)` at the event dates,
9,839 measurements) and `power_gate`, never retyped:

| cell | se (naive) | se (clustered, worst case) | MDE80 naive | MDE80 clustered | power vs the hypothesised effect |
|---|---|---|---|---|---|
| full × `h`=63 | 0.240pp | 0.602pp | **0.68pp** | **1.71pp** | **99.9% / 51.7%** |
| full × `h`=126 | 0.339pp | 0.852pp | **0.96pp** | **2.42pp** | **100% / 81.3%** |
| tier × `h`=63 | 1.505pp | 2.483pp | 4.28pp | 7.06pp | 12.1% / **7.2%** |
| tier × `h`=126 | 2.129pp | 3.513pp | 6.05pp | 9.98pp | 20.0% / **10.0%** |

**BOTH BOUNDS ARE LABELLED AND THEY BRACKET THE TRUTH FROM OPPOSITE SIDES.** The dispersion is
*trailing*, and volatility is clustered, so post-event dispersion **exceeds** it — that bound
**overstates** power. The cluster inflation is `sqrt(n/G)`, the worst case of perfect within-ticker
correlation — that bound **understates** it. **Neither is the arm's own standard error, and the MDE
that travels with the verdict must be the arm's own** (`MB8`: never borrow an `se`).

**THE HONEST SUMMARY:** the wide universe can see the hypothesised effect at `h = 126` under either
bound and at `h = 63` under the optimistic one; **the tier cannot see it under either.** So this
register can answer §4b's question 1 — *is the signal real?* — and **cannot** answer question 2 —
*is it any use to the book we trade?*

---

## 9. What this is NOT, so the result is not over-read

**NOT NEW, and all three are this project's own measurements:**

* the `insider` **theme** is weak — IC *t* **-0.24**;
* **re-filtering that theme's rows cannot move the blend** — `MB20` changed the score on **54.83%**
  of scored cells and the composite's per-date rank correlation between arms was **0.9774**, top-25
  overlap **22.65 of 25**, and it **ADOPTED NOTHING**;
* **dip × insider open-market buying was NULL** — `V6-B` arm 3, +1.147pp/yr full sample with a late
  half of **+0.011pp**.

**NEW:** none of those tested a **standalone event signal**. `MB20` re-scored a theme at 1/7 weight;
`V6-B` conditioned on a dip first (and K2 exists so this register does not quietly become that
arm); and the theme's IC is a cross-sectional rank statistic on a 69-date quarterly panel, which
`SEARCH_DOCTRINE` §1.4 measures as the **weakest space this project has** — 80%-power MDE
0.4274–0.5071 SD, *"a merely good new signal is invisible there BY CONSTRUCTION."* **This is event
time on the daily series.** So a null here is a different null, and a pass would contradict none of
the three.

---

## 10. Trials

**FOUR EQUITY TRIALS**, booked **BEFORE any runner exists**: 2 horizons × 2 populations. The two
tier cells are computed and reported even though K1 fires on them, because Stage 1b makes the tier
reading **govern advancement** and a population that is not looked at cannot govern anything.
**Charging them is the safe direction** (`MA6`: overstating `N` raises every bar). The `k = 3` and
`h ∈ {5, 21}` sensitivities carry **no verdict** and are **not** charged separately; the register
declares them so they cannot be promoted after the fact.

---

## 11. Void conditions

1. **Any bar above is changed after a cell has been seen to fail it.** `W-28`'s rule: a bar may be
   RAISED and never LOWERED once watched.
2. **The strict condition of §2a is dropped**, or the broad sensitivity is promoted to primary,
   after seeing which reads better.
3. **A horizon or a `k` outside §5 is given a verdict**, or a sensitivity is quoted as a result.
4. **One return definition is quoted without the other** (§4).
5. **The CHECK quadrant (2020–2026 × half 1) is read at all.** It is counted in the census for
   feasibility — **5,152 strict events** — and that count is not a look at an outcome. Stage 2 gets
   one read and this register does not spend it.
6. **A tier null is reported as absence** rather than as `UNDERPOWERED-BY-CONSTRUCTION` with its
   7.2% / 10.0% power attached.
7. **A floor is borrowed** from X7 or `CORRECTED-FLOORS` (§6 A3).
8. **The pre-2009 era is read as a Stage-3 confirmation.** It is **FORECLOSED BY CONSTRUCTION and
   that is declared now**: the strict definition leaves **105 events** before 2009, because a pair
   needs two prior years of observable trading and the file's early coverage cannot supply it. A
   register that later quotes those 105 events as an out-of-sample check is quoting noise.

---

## 12. Expectations, stated now

Forecasts, not findings; they carry no weight in any verdict.

1. **The wide-universe `h = 63` cell is POSITIVE but fails A4 (the 0.67pp cost floor)**, at 55/45.
   The literature's long-short rate halved and netted of a round trip leaves very little.
2. **The tier returns UNDERPOWERED, as §7 already declares**, at 95/5 — this is nearly a deduction
   and is scored as such.
3. **K2 does NOT fire**, at 70/30: insiders buy after falls, but a 30-day filing window is wide
   relative to a 5-session dip window.
4. **K3 does NOT fire**, at 85/15: the theme is a scored quantity on 94,660 cells and the event
   flag fires on 8,478 of millions.
5. **At least one cell's halves disagree in sign**, at 60/40.
6. **The verdict overall is NULL**, at 70/30.

---

## 13. Not done, named so it is not mistaken for done

* **No Stage 2, no check-quadrant read, no Stage 3** — and §11.8 forecloses Stage 3 by construction
  rather than by choice.
* **No options expression.** The scout's arithmetic closed that and `SELL-PREMIUM-2`'s
  premium-selling route on this event is a **different register in a different family**, not an
  amendment here.
* **Nothing is adopted.** Adoption is Don's and is a vintage event, and under `DECISIONS.md`
  2026-10-06 any candidate goes to him **quoted at half its backtested size** (McLean-Pontiff).
* **No sell-side arm** (`transactioncode == "S"`), no net-buying construction, no size-weighted
  cluster, no officer/director split. Each is a new hypothesis and needs its own register.
* **`MB20` is not re-opened, `V6-B` is not re-opened, and the `insider` theme's weight is not
  touched.**

---

## AMENDMENT 1 — 2026-10-13, BEFORE ANY OUTCOME EXISTS: every count above is RESTATED, and the correction makes the design HARDER

**A DEFECT IN THE IMPLEMENTATION, NOT IN THE RULE, AND THAT DIRECTION IS WHAT MAKES THIS A FIX.**
Rule 5 above says *"a busy quarter at one name cannot re-fire the same cluster"*, and the first
implementation suppressed a repeat only on the **same day** — so the very next filing re-fired the
same cluster. Found on the banked event set before any arm ran: `ISCA` returned **29 insiders on
2008-01-04, 01-07 AND 01-08**, one cluster counted about twenty times. The register's stated rule
was right and the code did not implement it, so the code changed.

The repair is a cooldown of one whole window, so fired windows cannot overlap and each cluster
contributes exactly once. **It removes about half the events, which REDUCES power** — the direction
that makes the design harder, discovered before any outcome existed.

**THE VERDICT STRUCTURE IS UNCHANGED**: `h = 63` and `h = 126` are still the only horizons whose
hypothesised effect clears the cost floor and whose required `n` is met on the wide universe, and
the governing tier still fails at every horizon. Only the numbers move.

### Restated — §2a, the strict condition's cost

**4,386 strict build-cell events against 11,562 broad**, so the strict form costs **62.1% of the
sample** (the original text said *"two thirds"* of 8,478 against 25,304; the fraction survives, the
counts do not).

### Restated — §3, the population

| population | events | ticker clusters | early / late |
|---|---|---|---|
| **FULL corrected universe** | **4,386** | 1,344 | 2,398 / 1,988 |
| **TIER, `cap >= $10B`** | **146** (3.33% of the cell) | 79 | 45 / 101 |

### Restated — §5, the horizons

| `h` | hypothesised effect | clears the 0.67pp cost floor | required `n` | full universe (4,386) |
|---|---|---|---|---|
| 5 | 0.10pp | NO | 30,614 | NO |
| 21 | 0.41pp | NO | **7,289** | **NO** (it cleared before the repair) |
| **63** | 1.23pp | YES | **2,430** | **YES (1.80×)** |
| **126** | 2.46pp | YES | **1,215** | **YES (3.61×)** |

`h = 21` now fails the required-`n` as well as the cost floor. **It was already a no-verdict
sensitivity for the cost-floor reason**, so nothing about its status changes — recorded because a
reader comparing the two tables would otherwise see a cell move from clearing to failing and
wonder which reading governs.

### Restated — §7 K1, and §8, the power

The tier carries **146 events against 2,430 required at `h = 63` and 1,215 at `h = 126`** — short
by **16.6×** and **8.3×**.

| cell | se (naive) | se (clustered, worst case) | MDE80 naive | MDE80 clustered | power vs the hypothesised effect |
|---|---|---|---|---|---|
| full × 63 | 0.322pp | 0.582pp | **0.92pp** | **1.66pp** | **96.5% / 54.5%** |
| full × 126 | 0.456pp | 0.824pp | **1.30pp** | **2.34pp** | **100% / 83.8%** |
| tier × 63 | 1.767pp | 2.402pp | 5.02pp | 6.83pp | 10.0% / **7.4%** |
| tier × 126 | 2.499pp | 3.397pp | 7.10pp | 9.65pp | 15.6% / **10.4%** |

**The conclusion is unchanged and is now on smaller numbers: the wide universe can see the
hypothesised effect, the tier cannot.**

### Restated — §11.5 and §11.8

The check quadrant holds **2,669** strict events (counted for feasibility, **not read**). The
pre-2009 era holds **31** — down from 105, so Stage 3 is **more** foreclosed, not less, and §11.8
binds a fortiori.

### The kills, run in their own pass and read before any arm

All three **stopping** kills PASS; K1 marks exactly the two cells this register already declared.

* **K2 — the dip overlap: 0.2048 against a bar of 0.25. It does NOT fire, and it does not clear
  comfortably.** 20.5% of clusters follow a `DIP-CALL` event within 5 sessions, 4.5pp under a bar
  fixed before the measurement. **So roughly one cluster in five IS a post-dip event, and any
  reading of a positive result has to carry that** — it is not `V6-B`'s arm, and it is not disjoint
  from it either.
* **K3 — the costume check: the worst theme is `insider` itself at 0.1699 against 0.60.** The flag
  is not the theme in disguise, which is what makes §9's *"this is a different null"* a measurement
  rather than an assertion.
* **K4 — look-ahead: zero events dated before their own window**, with the positive control
  detecting a planted ROUTINE pattern and the negative control leaving a planted opportunistic one
  alone. A guard that refused everything would pass the first and fail the second, which is why
  both run.
* **The tier's PER-DATE NAME COUNT clears Stage 1b's floor on every date** — 44 dates, min **106**,
  median 256, max 342, zero below `CONTRACT_MIN_POSITIONS` = 50. **So the tier's failure is purely
  an EVENT-count failure and not a name-count one**, which is the sharper statement: the tier is
  large enough to trade and the signal fires too rarely inside it.
