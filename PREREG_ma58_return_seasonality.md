# PRE-REGISTRATION — MA58 · Cross-sectional return seasonality

**Written and committed BEFORE any measurement code exists.** This file is committed **ALONE** —
one `.md`, zero `.py` — and is a strict git ancestor of every commit that measures anything. If a
`.py` file appears in the same commit, this register is **VOID**.

Ledger row **`MA58`** (`VALQUO_LEDGER.md:573`), `DESIGN-RECORDED — NOT RUN; PREMISE VERIFIED`.
Literature: Heston & Sadka (2008), *Seasonality in the cross-section of stock returns*;
Keloharju, Linnainmaa & Nyberg (2016), *Return seasonalities*.

**ADOPTS NOTHING.** No file under `valuation/` changes. Nothing is added to
`settings.NUMBER_THEME` — the arm is a study column computed in a script, so
`tests/test_ma_final_batch.py::test_ma58_no_seasonality_signal_has_been_registered_without_a_register`
stays green **and is correct to stay green**. A positive result would license a *separate*
adoption item, not an edit here.

---

## 0 · PREMISE FINDINGS — measured BEFORE this register was written

Facts about what data exists and what the shipped objects are. They are not results, they cost no
trials, and **each one changed the design below**. Recorded here so the design reads as a
consequence of them rather than as a choice made after seeing an outcome.

### 0.1 · The ledger row's premise holds

`settings.NUMBER_THEME` has **53** entries and none is seasonality-shaped (re-verified). The
project has never tested return seasonality. The row's own refinement stands: `Linnainmaa` appears
twice in `VALQUO_EDGE_AUDIT.md` for *different* papers (Ball–Gerakos–Linnainmaa–Nikolaev; and
Ehsani–Linnainmaa), so an author grep reads as "already covered" and is wrong.

### 0.2 · The banked panel **IS** the shipped panel — reproduced bit-for-bit, not assumed

`data/free_analysis/panel_corrected_69d.pkl` (113,945 rows, 69 dates 2009-01-15 → 2026-01-28,
2,531 names) scored through the shipped `quantile_backtest` at flat 1/7 returns:

```
top_decile_alpha    0.07174142332098163      record 0.07174142332098163
long_short_tstat    2.8360640685320595       record 2.8360640685320595
monotonicity       -0.8909090909090909       record -0.891
equal_weight_ann    0.18137118752419476      record +18.137%
long_short_ann      0.11038184616720666      record +11.04%
```

Seventeen significant figures on the two headline cells. **No panel rebuild is required**, and C1
(§5) re-runs this as a *gate* rather than resting on this paragraph.

### 0.3 · The price cache is bit-identical to the licensed CSVs

`data/free_analysis/S17_PRICES.pkl` is a `ticker → (dates, closes)` dict over 2,985 tickers.
Checked against `data/backtest/prices/*.csv` for AAPL, MSFT and A: equal length, equal date
arrays, `max |Δclose| = 0.000e+00`, **0 mismatches**. **100.0% (2,531/2,531)** of panel names have
a series. Series start: min 1997-12-31, median 1999-06-11.

`close` is `closeadj` — split- **and** dividend-adjusted, i.e. **TOTAL return**
(`panel-returns-are-total-return`). That is the correct basis for a past-return signal and it is
the same basis the panel's own `momentum` theme uses.

### 0.4 · DEPTH — and the ledger row's own prediction is **REFUTED**

The row states: *"DEPTH BINDS AT THE PANEL'S EARLY END — a 20-year lag structure is unavailable in
2009 with prices starting 1997-12-31, so the arm is either a covered-subsample test on the
S18/U2/U3/V6-OPT protocol or a shallower lag set applied uniformly."*

The first half is true: 20 annual lags are unavailable **anywhere** in this panel, and the deepest
uniform depth the data supports at the first rebalance date is **K = 11**. The second half —
that this forces a covered-subsample — **is false, and it is false in the direction that makes the
item stronger.** Measured, requiring **all** K seasonal **and all** 3K non-seasonal windows to be
computable (§2.1), a name-date is *eligible*:

| K | eligible rows | min names/date | median/date | first date | last date | dates < 100 |
|---|---|---|---|---|---|---|
| 3 | 90.00% | 1,400 | 1,457 | 1,400 | 1,723 | 0 |
| 5 | 84.33% | 1,349 | 1,375 | 1,350 | 1,504 | 0 |
| 8 | 79.22% | 1,255 | 1,294 | 1,282 | 1,270 | 0 |
| **10** | **76.13%** | **1,199** | **1,268** | **1,201** | **1,221** | **0** |
| 11 | 74.56% | 1,161 | 1,236 | 1,161 | 1,191 | 0 |

**All 69 dates are covered at every depth, with never fewer than 1,161 names.** So this is the
first register in this lane in six attempts (S18, U2, U3, V6-OPT, MA31/MA32) where coverage does
**not** forbid a both-halves gate on the full panel. **No covered-subsample protocol is invoked.**

**And the shortfall is at the LATE end, not the early end** — the opposite of the row's
prediction. At K = 10 the first date is **81.6%** eligible and the last is **66.3%**. The panel
*grows* (1,471 names in 2009 → 1,842 in 2026) and the names it grows by are young: a 2021 listing
has no 2011 history. The early panel is small and made of long-lived names. **A depth requirement
on this panel is a recent-IPO screen, not an early-period screen.**

### 0.5 · The k = 1 seasonal window overlaps `momentum`'s tail — declared now, not discovered later

The k = 1 annual-lag window is `[t − 1y, t − 1y + 3mo]`, i.e. **12 to 9 months before t**, which
sits inside the trailing window `z_ret_12_1` is built from. So the seasonal signal is **not**
a priori orthogonal to the `momentum` theme. This is exactly why the gate is **incremental** IC
against the incumbents (§2.4) and not raw IC, and why C6 reports the correlation explicitly.

### 0.6 · What is NOT tested, named so it is not mistaken for tested

* **Monthly seasonality.** The published construction is same-*calendar-month*. This panel
  rebalances **quarterly** and its forward object is a 63-trading-day return, so the arm is
  same-*calendar-quarter*. A monthly test needs a monthly panel — `MA33` closed that permanently
  on `MA24`'s own pre-committed kill condition (MDE +0.012324 against a +0.009607 effect;
  ~188 months, i.e. ~2032). **This is a quarterly adaptation and must never be quoted as a
  replication of the monthly result.**
* **The 20-year lag structure.** Unavailable at any panel date. See §2.1.
* **Seasonality in anything but returns** (earnings seasonality, fiscal-quarter effects). Those
  are a different literature and the corpus's existing "seasonal" hits are all that other thing.
* **Adoption.** Nothing is wired, nothing is weighted, `NUMBER_THEME` is untouched.

---

## 1 · DISCLOSED PRIOR KNOWLEDGE

I have measured **nothing** about this signal's predictive content. §0 is coverage, provenance and
column identity — no IC, no residual, no return, no sort has been computed for either arm at any
depth. The depth in §2.1 was chosen on the availability table in §0.4 and on nothing else.

**The task that commissioned this states "Expect REJECTED".** My own prior agrees and is recorded
with numbers in §6. That prior is a reason to pre-commit the bars *harder*, not a licence to read
a marginal result as a pass — and equally not a licence to wave a clear pass away.

---

## 2 · DEFINITIONS — fixed here, not at runtime

### 2.1 · THE LAG STRUCTURE **IS** THE HYPOTHESIS — fixed now, and no other lag set may be read

Ledger constraint (1). Heston–Sadka's result is a **pattern across lags**: annual lags positive,
non-annual lags negative. Sweeping lags and reporting the best is the p-hacking this register
exists to stop.

For stock *i* at rebalance date *t*, with all windows spanning **3 calendar months** and priced
from the last close **on or before** each boundary (tolerance 10 calendar days; a wider gap makes
the window uncomputable, never imputed):

* **SEASONAL (annual lags), the arm `seas`** — mean simple return over
  `W(k, 0) = [t − k years, t − k years + 3mo]` for **k = 1 … 10**.
* **NON-SEASONAL (non-annual lags), the arm `nonseas`** — mean simple return over
  `W(k, m) = [t − k years + m months, + 3mo]` for **k = 1 … 10** and **m ∈ {3, 6, 9}** — the
  **other three quarters of those same years**. Thirty windows.

This is KLN's own contrast (*same calendar month, years 1–20* against *other calendar months,
years 1–20*) mapped onto the panel's native quarterly calendar. **It is the only lag structure
this register may read.**

**DEPTH: K = 10, and the choice is made here on §0.4's availability table alone.** It is the
deepest whole decade uniformly available at **every one of the 69 dates**; K = 11 is the true
maximum and buys 1 more year for 1.6pp of coverage; 20 is impossible. **A shallower or deeper K
may not be substituted after seeing a result.** K = 5 is run **once**, as control **C-DEPTH**
(§5), and **carries no verdict and cannot rescue or overturn A1** — reading a verdict off it is a
void condition (§8).

### 2.2 · The join — no window may end after *t*

Every window above ends at or before *t*: the latest is `W(1, 9) = [t − 3mo, t]`, which closes on
the rebalance date itself and uses that date's close — information available at *t*, and the same
basis the shipped `momentum` theme uses. **C3 asserts that no window uses any close dated after
*t*, on every row, and the run aborts if one does.**

### 2.3 · Eligibility, standardisation, and the incumbent set

* A name-date is **eligible** only if **all 10** seasonal **and all 30** non-seasonal windows are
  computable. **Both arms are therefore measured on IDENTICAL rows** — which is what makes the
  §4.2 contrast a comparison rather than two different samples.
* Each feature is z-scored **within each rebalance date over the eligible names only**, using the
  shipped `cross_sectional.zscore` (2% winsorisation — S21's finding).
* The **seven incumbent themes** are `value`, `quality`, `momentum`, `insider`,
  `capital_discipline`, `size`, `institutional` — the seven that carry weight. `low_risk`
  (zeroed), `growth` and `sentiment` (empty) are **not** incumbents.

### 2.4 · The verdict statistic — incremental IC, the PEAD/U2 template

Per rebalance date, on eligible rows only:

1. Cross-sectional OLS of the candidate z-score on the seven incumbent theme columns **with an
   intercept**. Rows missing any input dropped for that date; **≥ 20 names required**.
2. Keep the **residual** — the part the composite already in the panel cannot explain.
3. **Spearman** IC of that residual against `fwd_ret`. One IC per date.
4. `ic_tstat = mean / (sd / √n)` on that IC series — **the shipped `theme_ic` arithmetic**, so the
   number compared to a calibrated bar is the statistic the bar was calibrated on.

Reported as diagnostics carrying **no verdict**: raw (non-residualised) IC and its `ic_tstat`;
mean per-date R² of the candidate on the incumbents; coverage.

PEAD is why this is the gate and not raw IC: `pead_car` cleared a standalone bar at *t* +2.215 and
its **incremental** IC *t* was **+0.020**.

### 2.5 · SORTING or LEVEL — the `P1S0-CONTROL` clause, and it is mandatory

`P1S0-CONTROL` returned NULL because its two legs asked different *kinds* of question: leg 1 asked
whether the panel **SORTS** and leg 2 asked whether a decile's cumulative alpha is **POSITIVE**,
and the full panel's early window is exactly the case where those disagree (cum alpha +0.0604
while monotonicity is +0.152 and the long-short *t* is −0.846).

**Every leg in this register asks a SORTING question and there is no level leg.**

| leg | question | kind |
|---|---|---|
| A1 `seas` | does the seasonal residual **rank** forward returns? | **SORTING** |
| A2 `nonseas` | does the non-seasonal residual **rank** forward returns? | **SORTING** |
| contrast | is A1's rank statistic **larger** than A2's? | **SORTING** (difference of two sorting statistics) |

**A level question — cumulative alpha, decile return, hit rate, or any statement about a
portfolio's return LEVEL — may not be added to the verdict rule, before or after the run.**
Reading one is a void condition (§8). Decile returns may be *reported* as colour; they carry no
verdict.

---

## 3 · BARS

| bar | value | status **on this run** |
|---|---|---|
| theme IC *t* | **2.71** | X7's calibrated p95 — a **MILD extrapolation**, see below |
| own within-date permutation p95 / p5 | measured | **calibrated on this exact object** |

**The 2.71 is a mild extrapolation and must be labelled so every time it is quoted.** X7
calibrated it on the full 69-date, 2,531-name panel at h63. This run uses **the same 69 dates**
and the same horizon, on a **narrower cross-section** (~1,268 names/date against ~1,650; 76.13% of
rows). The date count — which sets the IC series length and hence the *t* — is **identical**.
That is a far smaller transfer than U2's 40-date subsample, and it is still a transfer.
**Re-calibrating on this subsample is not attempted**; doing it after seeing the arms is the error
this project has already paid for twice.

`ic_tstat` is the statistic compared to 2.71. **`ic_inference.t` may NEVER be compared to 2.71**
(audit M2's explicit prohibition).

**The second bar is each arm's OWN null and it is the one I trust more here.** 500 within-date
permutations of the candidate column (the within-column scheme —
`x7-permutation-cannot-calibrate-a-score`: `placebo_panel` is exactly invariant on a composite and
would return a null equal to the real book), preserving each date's distribution and missingness,
recomputing the **full** residualisation and IC each draw. Both bars must clear.

**POWER CONTROL — MANDATORY, AND IT GATES INTERPRETATION.** `z_gp_on_capital` and `z_ret_6_1`
(coverage 97.13% and 98.30%) are scored raw and residualised on the **identical eligible rows**.
**If NEITHER clears raw `ic_tstat` 2.0, every null in this register is reported as
UNINTERPRETABLE — "could not be separated at this resolution" — and NOT as a negative result.**
Fixed now, before the controls have been run.

---

## 4 · VERDICT RULES

### 4.1 · Signs, declared before running

* **A1 `seas`: POSITIVE.** Heston–Sadka / KLN: same-season past returns predict *positively*.
* **A2 `nonseas`: NEGATIVE.** Their non-annual lags are *negative*. A positive A2 does not
  reproduce the published sign, and §4.2 says what that means.

A result of the wrong sign is a **failure to reproduce the published direction**, never a pass.

### 4.2 · The rule

Halves, on the project's convention (V6's exact split): **early = 2009-01-15 → 2017-04-20 (34
dates), EMBARGOED = 2017-07-20, late = 2017-10-18 → 2026-01-28 (34 dates).**

**A1 clears** iff, in **BOTH** halves *and* on the full sample:
&nbsp;&nbsp;(a) incremental `ic_tstat` **≥ +2.71**, **AND**
&nbsp;&nbsp;(b) incremental `ic_tstat` **≥ its own permutation p95**.

**The contrast clears** iff, in **BOTH** halves, the paired per-date difference
`IC(seas) − IC(nonseas)` is **positive** and clears **its own** permutation p95.

| verdict | condition |
|---|---|
| **REPLICATED** | A1 clears **and** the contrast clears |
| **NOT-SEASONAL** | A1 clears **and** the contrast does **not** |
| **REJECTED** | A1 does not clear |
| **UNINTERPRETABLE** | neither power control clears 2.0 |

**`NOT-SEASONAL` is the discriminator and it can only make the verdict harder, never easier.** If
the non-seasonal windows predict as well as the seasonal ones, then whatever A1 found is
information in **past returns generally** and there is nothing seasonal about it. That is a
materially different claim from the paper's, and it may not be reported as MA58 replicating.

**Ambiguity is a NULL** (`RUN_RULES` A6). A cell that misses its bar misses it; nothing is
rounded, and no bar is relaxed after the fact.

### 4.3 · What is NOT licensed by a pass

A `REPLICATED` verdict licenses **an adoption register**, not an adoption: wiring a signal into
`NUMBER_THEME` is a construction change and therefore a **VINTAGE EVENT** (five-year clock reset,
Don's call). It also would not license the monthly claim (§0.6).

---

## 5 · CONTROLS — every one fixed now; C1, C2 and C3 are **GATES**

* **C1 — GATE.** The panel reproduces the published record at the five cells in §0.2. Computed and
  **read in its own pass**; the run **aborts before any arm is scored** if it fails. (Session 26's
  defect: a gating control and its outcomes in one pass is not a gate. `MA31`/`MA32` repaired it;
  this repeats the repair.)
* **C2 — GATE.** Eligible-row counts reproduce §0.4's table at K = 10 (76.13% of rows, min 1,199,
  all 69 dates ≥ 100). A mismatch means the feature builder is not the object this register was
  written about.
* **C3 — GATE.** **Zero** windows use a close dated after *t*, over all eligible rows.
* **C4.** The two arms are measured on **identical** `(date, ticker)` key sets — asserted equal,
  not assumed.
* **C5.** `seas` and `nonseas` are not the same column: within-date Spearman between them is
  reported, and a value **> 0.90** flags the contrast as degenerate (the `skew_25d` /
  `illiq`-`spread_pct` duplicate class).
* **C6.** Mean per-date correlation of each arm against **each** of the nine theme columns,
  reported in full. `momentum` is the one to read first (§0.5).
* **C-DEPTH.** The identical pipeline at **K = 5**, run **once**, reported whatever it says.
  **Carries no verdict.**
* **C-DEGEN.** `theme_ic`'s zero-variance guard is `sd > 0`, and whether a constant series has an
  exactly-zero float sd is value-dependent (U2's finding), which can return `t ≈ 1e16`. A
  degeneracy check gates the verdict so an absurd *t* can never be **read** as a pass.

---

## 6 · EXPECTATIONS — written before any arm has been run, scored afterwards whatever they say

| # | prediction | odds |
|---|---|---|
| 1 | **A1 is REJECTED** — fails (a) or (b) in at least one half | 80/20 |
| 2 | A1's **raw** IC *t* exceeds its **incremental** IC *t* (incumbents absorb much of it) | 70/30 |
| 3 | Mean per-date R² of `seas` on the seven incumbents is **< 0.25** (it is mostly new information) | 60/40 |
| 4 | A2's sign is **POSITIVE**, i.e. the published non-annual negative sign does **not** reproduce | 55/45 |
| 5 | The contrast fails its permutation p95 in at least one half | 75/25 |
| 6 | At least one power control clears raw `ic_tstat` 2.0 on the eligible rows | 85/15 |
| 7 | Mean per-date correlation of `seas` with the `momentum` theme exceeds **+0.20** | 55/45 |

Predictions 2 and 3 are deliberately in tension: I expect the signal to be *largely* new
information (3) while still expecting the incumbents to absorb a visible share of a raw IC (2).
If both hold, the honest reading is that the incremental gate is doing real work rather than
either rubber-stamping or gutting the arm.

---

## 7 · TRIAL COST — pre-committed, and booked BEFORE the run

**Two arms, two equity trials: A1 `seas`, A2 `nonseas`. Equity `N` 232 → 234.**

Charged to **equity**, not options: the arms predict a **stock's** forward return (the `U2` /
`MA31` / `MA28` precedent). Options `N` untouched at 297, infra at 15.

Controls, the power check, the coverage measurement and **C-DEPTH** charge **zero** — they search
nothing and none may return a verdict. A2 is charged in full even though it can only make the
verdict harder: **overstating `N` is the safe direction**, and the ledger row budgets 1–2.

**The budget is booked in `RESEARCH_LOG.md` in its own commit BEFORE the measurement runs**
(`MA28-CARD` / `P1S0-CONTROL` precedent, `7f294df` / `be4bd36`). The verdict cell reads
`PRE-REGISTERED` and is filled **in place**; a second row would double-charge one hypothesis.

`N` was **re-read from `research_log.detail()` after merging `origin/main`** for this register and
must be re-read again before the results commit — it has moved under this lane before.

---

## 8 · VOID CONDITIONS — this register returns **NO VERDICT** if any fires

1. A `.py` file appears in this register's own commit.
2. Any lag structure other than §2.1's is **read for a verdict** — a different K, a different
   window length, a monthly variant, or a subset of the ten annual lags chosen after the fact.
3. **C-DEPTH (K = 5) is used to rescue, overturn or replace A1's verdict.**
4. A **LEVEL** statistic (cumulative alpha, decile return, hit rate) enters the verdict rule
   (§2.5).
5. A bar is moved, or a half is redefined, after any arm has been read.
6. C1, C2 or C3 fails and an arm is scored anyway.
7. The arms are scored on non-identical row sets (C4 fails) and the contrast is reported anyway.
8. Anything is added to `settings.NUMBER_THEME`, or any file under `valuation/` changes, in the
   results commit.
9. A verdict is reported without its coverage figure and without the labelled extrapolation status
   of the 2.71 bar.

---

*Committed alone, markdown only. Trial budget booked separately and before the run.*
