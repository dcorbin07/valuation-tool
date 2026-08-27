# PREREG DRAFT — DC-1: THE DIP-CONFIRMATION REGISTER
## Fundamentals intact · price falls on narrative · the next report falsifies the narrative
## **Draft only. Frontier Scout lane, 2026-08-26. Zero trials charged by this file.**

**Trials if adopted: 1, equity** (242 → 243 at this writing; hurdle **3.3133 → 3.3145** —
re-read at run, `MA37`). Commit ALONE, markdown only, a strict ancestor of every measurement
commit.

---

## 0. PROVENANCE — this hypothesis was selected on its outcome, and that governs everything below

The mechanism was generated from **two names Don currently holds, both of which recovered**:
NOW (−59.6% peak-to-trough, +10.0% today) and CRM (−46.6%, +22.6% today). **That is selection
on the outcome three times over** — the names were chosen after the recovery, they are held (so
the ones that did not recover are not in the sample of things noticed), and the "today" figures
are the recovery itself. **Two winners are a hypothesis, not evidence, and this register treats
them as the former without exception.**

Three consequences, pre-committed:

1. **Neither name's 2026 episode may enter the test.** They postdate the panel, so exclusion is
   automatic today — and it is fixed here in writing so that a later panel extension cannot
   quietly include them. **If the panel is ever extended past 2026-01-28, NOW and CRM are
   excluded by name and the exclusion is reported.**
2. **A positive result on the panel is the FIRST evidence for this mechanism, never a
   confirmation of it.** The register's write-up may not use the word "confirms" about the
   examples, and may not cite them as corroboration of its own result.
3. **The examples may not shape any parameter.** No threshold, window, or screen in §6 is chosen
   to make NOW or CRM qualify, and none was: every bound is either imported from an existing row
   or set on the record's own conventions. Pinned by an AST/text test over the register that
   neither ticker appears in the scoring path.

---

## 1. THE MECHANISM, AS A FALSIFIABLE CHAIN

1. A name's fundamentals are intact at quarter *Q1* (no deterioration on measurable flags).
2. Its price falls hard on a **narrative** — here, AI-displacement — rather than on delivered
   numbers. Operationally: **the drawdown is not accompanied by fundamental deterioration.**
3. At *Q2* the company reports and the fundamentals are again intact. **The narrative's central
   prediction — that the numbers would deteriorate — is falsified on a dated, observable event.**
4. The price re-rates toward the fundamentals it never stopped delivering.

**The payoff arrives at the event, not across the calendar.** That single claim is what makes
this register different from `V6`, and §2 is about whether the difference is real or rhetorical.

**The efficient-market objection, stated by me rather than left for a reader:** why would a
scheduled, widely-anticipated report produce a predictable re-rating? The available answers —
limited attention, narrative persistence, slow diffusion of disconfirming evidence — are the
same answers PEAD gives, and **PEAD is REJECTED on this panel**. That is the single most
hostile fact in this draft and §3 does not soften it.

---

## 2. WHY THIS IS NOT `V6` RE-RUN — the clock, quantified — AND WHAT THE RE-CLOCK DOES NOT EXCUSE

**`V6` measured calendar horizons (63d, 126d) from the dip and returned NULL on all four arms.**
The re-open rule permits a new *design*, not a new *attempt*, so the clock difference has to be
worth something specific. Here is the arithmetic that says how much.

**If the payoff is concentrated at one event**, let `J` be the jump, `σ_d` the daily abnormal-
return SD, and `σ_e` the event-day abnormal-return SD. Then:

* a **W-session calendar window** yields `t ≈ J / (σ_d·√W)`
* an **event-window** measurement yields `t ≈ J / σ_e`
* the ratio — the detection gain from re-clocking — is **`(σ_d·√W) / σ_e = √63 / k`** where
  `k = σ_e/σ_d`.

| `k = σ_e/σ_d` (event-day vol multiple) | detection gain over `V6`'s 63-day window |
|---|---|
| 2 | **≈ 4.0×** |
| 3 | **≈ 2.6×** |
| 4 | **≈ 2.0×** |

**A 2–4× improvement in t is not a rounding error; it is the difference between a null and a
finding.** That is the honest case for the register.

### And here is what the re-clock does NOT excuse — four things

1. **`V6`'s window usually CONTAINED the event, so its null is diluted evidence against this
   mechanism too — not silence about it.** Earnings arrive roughly every 63 trading days, so a
   63-session window from a randomly-timed dip contains the next report most of the time. `V6`
   did not miss the event; it **measured the event plus ~62 sessions of noise, entered at the
   wrong point.** This register improves the *signal-to-noise ratio*, **not the effect size** —
   and if `V6`'s nulls reflect no effect at all, event-timing finds a sharper nothing.
   **This is the basis of kill K1 (§8), which can end the register before it scores anything.**
2. **It does not excuse the entry change.** Moving the entry from the drawdown to the
   confirmation makes it **a different trade with a PEAD-shaped prior** (§3), and that must be
   argued, not smuggled in under the clock argument.
3. **It does not excuse the provenance.** §0 stands whatever the clock.
4. **It does not overwrite `V6`.** `V6`'s four nulls stand as measured, on their own terms, and
   this register may not be cited as having "corrected" them. It asks a re-clocked question.

---

## 3. THE GRAVEYARD, ROW BY ROW — argued past, or the draft dies here

| row | what it measured | how DC-1 stands against it |
|---|---|---|
| **`V6`** — NULL on all four arms | quality-conditioned drawdown recovery over **calendar** 63d/126d from the dip | §2: a new clock and a new entry point, with the detection gain quantified in advance and **K1 pre-committed to kill the register if even the re-clocked implied t falls short**. `V6` is not overwritten |
| **`V6-B`** — healthy dips fall a further 20% **10.8pp less often** (HAC t −10.5847) | **SURVIVAL — the probability of a further fall.** Not return | **This draft may NOT quote `V6-B` as return evidence, anywhere, and a text test enforces it.** A lower probability of further decline is not an expected-return claim; conflating the two is exactly the error `V6-B`'s own row guards against. `V6-B` supports only the *screen* (that intact-fundamentals dips are a distinguishable population), never the payoff |
| **`E-2`** — Δcomposite / fundamental momentum, **NULL on both bases** | the *change* in a name's composite score as a cross-sectional signal | DC-1 is **not a change-in-score signal**. Its trigger is a dated event and a falsified expectation, not a score delta. **But the overlap is real enough to need a kill:** K3 tests correlation against the banked Δcomposite column, and `E-2`'s null is the reason the prior in §11 is low rather than moderate |
| **PEAD** — built, gated, **REJECTED** on this panel; `z_pead_car` and `z_pead_drift` already exist as columns | post-earnings-announcement drift keyed on the **surprise versus analyst estimates** | **The nearest neighbour and the most likely costume.** DC-1's claim keys on a different quantity — the gap between **price-implied expectations** and **delivered fundamentals**, which can be large when the estimate surprise is ~zero (a name can miss slightly and still falsify "the business is being displaced"). **That distinction is a hypothesis, not a fact, so it is enforced as a PRE-OUTCOME kill (K2) against both banked PEAD columns — never discovered afterwards.** If DC-1 is PEAD wearing a dip's name, it dies free |
| **THE VALUE THEME** — deployed incumbent | cheapness | **The most likely costume, and nearly by construction: a name that falls 50% without deteriorating IS cheap on every ratio.** Enforced two ways: K4's correlation kill against the value theme, **and** a mandatory descriptive report of the arm population's value-quintile distribution. If DC-1's population is simply the value theme's top quintile with a date attached, the register says so |
| **`MB18`** — the implied-growth expectations gap, **REJECTED**, largest abs t 1.5617 against 2.71 | the gap as a **standing cross-sectional level** | If the expectations-gap leg is used at all, it is used as a **change at a dated event**, not a level — a genuinely different object, but **on thin ice**, and `MB18` is the reason §6 makes it a *declared secondary* rather than the primary. `MB18`'s own finding that the sign lived in the solver's **censoring** (30.0% of rows bounded) travels as a mandatory partition |
| **`S7`** — casual interactions closed; **`S10`** — the book's worst drawdown is ONE market-wide quarter | interaction-hunting; drawdown concentration | DC-1 is a **conditioned event study**, not an interaction sweep — one pre-named conditioning set, fixed here. `S10`'s lesson enters as **K5**: if the qualifying events concentrate in a single market episode, the result is an episode and not an effect |
| **`B12`** | the alphabetical-slice era | irrelevant to the current panel, cited so nobody re-raises it |

---

## 4. INSTRUMENTS THE ARM NEEDS — and they did not exist when `V6` ran

* **`I-4`'s event spine, as repaired by `W-3b`** — **required.** This is what makes event-timing
  possible at all. **And `W-3b`'s own finding binds the design: "code 22 turns out to be broader
  than earnings."** The spine must be **filtered to actual earnings announcements**, with IBES
  actuals (`anndats`) as the authority and code-22 rows as the cross-check; **the disagreement
  rate between the two is reported** (control C4). An event study keyed on a broader event class
  than it claims is measuring something else.
* **`MA28`'s three flags** — **required**, as the *deterioration screen* (the "fundamentals
  intact" leg at both Q1 and Q2). Published thresholds, never re-fit. **Note the fourth flag is
  gone** (Audit Analytics unsubscribed), so this is a three-flag screen and the register says so.
* **`S23`'s fair-value panel** (108,241 rows, 69 dates, 2,441 names) — **optional, secondary
  only.** It supports the expectations-gap leg under `MB18`'s caveats. The primary arm does not
  need it, and the register is better without it if coverage is thin.
* **`I-3`'s crash-count library** — not needed. This is a return question, not a crash question,
  and borrowing risk machinery here would repeat `V6-B`'s conflation.

---

## 5. STAGE 0 — THE CENSUS, ON THE ARM'S OWN POPULATION, BEFORE THE ARM

*(The drafting rule adopted after `O-1` returned UNDERPOWERED on a coverage figure imported from
a different population: **coverage is measured on the population the arm will test, and stated
before the arm.** `O-1` assumed ~75% and the truth was 5.89%. This section exists so DC-1 cannot
repeat it.)*

Counted and banked **before any return is read**, reported per half:

1. Name-dates meeting the **drawdown** definition (§6a).
2. Of those, **MA28-clean at Q1** (the "no deterioration" leg).
3. Of those, carrying an **identified earnings event** in the repaired spine within the window,
   with IBES `anndats` present — **and the count that fails only for want of a date**.
4. Of those, **MA28-computable at Q2** (the confirmation leg needs the flags at the later date).
5. Of those, carrying `S23` rows (secondary leg only).
6. **The number of distinct market-wide drawdown EPISODES** the qualifying events fall into, and
   the share falling in the largest one.

**The intersection of 1–4 is the arm's population.** Its size, its per-half split, and the
episode structure at 6 are the inputs to §7's power line — **all of them derived here, none
imported from `V6`, `V6-OPT`, or any other study.**

**Free floors, fired at stage 0:** fewer than **16 date-clusters per half** (`S18`'s floor) →
**UNPOWERED-BY-CONSTRUCTION**, register stops, zero trials charged. Population below the §7
table's viable `n_eff` → same outcome, same cost.

---

## 6. THE ARM

### (a) Definitions, fixed here

* **Drawdown:** ≥ 30% below the trailing 252-session high as of the qualifying date, using
  **as-traded** prices for the drawdown computation (`B1`/`U1-SPLIT`; adjusted closes only for
  return computation). *(30% rather than `V6`'s 20% is set on Don's stated mechanism — a
  narrative-scale repricing, not an ordinary pullback — and it is fixed before any outcome. It
  is NOT swept; a sweep is a different register at a different price.)*
* **Fundamentals intact:** **0 of 3** `MA28` flags at Q1 **and** at Q2, published thresholds.
* **The confirming event:** the first earnings announcement after the qualifying date, from the
  repaired spine, **filtered to earnings** per C4.
* **Abnormal return:** market-adjusted against the panel's own benchmark, fixed in advance;
  a factor-adjusted variant is a **declared secondary**, reported, carrying no separate verdict.

### (b) The three designs hiding in the mechanism — named, because they are not the same trade

* **(A) Dip-entry → hold THROUGH the confirming report.** You own the re-rating jump. This is
  `V6`'s entry with an event-timed exit, and it is the design `V6`'s null speaks to most directly.
* **(B) Confirmation-entry → hold N sessions after the report.** You own only the drift *after*
  the jump. **This is PEAD's shape**, and it inherits PEAD's rejected local prior.
* **(C) Dip-entry conditional on PREDICTING confirmation.** Requires a prediction instrument
  nobody has built. **Not testable and not proposed.**

**Don's brief specifies entry at the confirmation, i.e. (B). This draft recommends (A) as the
PRIMARY and (B) as a declared secondary under the same register — and says so plainly so he can
overrule.** The reasoning: (A) captures the payoff the mechanism actually describes (the
re-rating on falsification), while (B) captures only what is left after the market has already
re-rated — which is PEAD, on a panel where PEAD was rejected. **Running both under one register
decomposes the payoff into the jump and the post-jump drift**, which is the informative split and
costs one trial, not two (`MA26-A`/`MA28`/`MA54-1` collapse precedent).

### (c) Statistic and verdict rule

**Primary:** mean abnormal return over the event window **[0, +1] sessions** around the
confirming report, on the arm population, against a **matched control**: drawdown-qualifying,
MA28-clean names *without* the narrative condition being tested — **and, more importantly, the
same names' own non-confirming quarters**, so the comparison is within-name where possible.
**Bar:** |t| > 3.3145 (re-read at run) **on a date-block-clustered standard error**, and
**sign-agreement across both halves**. Ambiguous against its own threshold is NULL (`RUN_RULES`
A-6). **Declared secondary, no separate verdict:** the (B) drift window [+2, +21].

---

## 7. POWER — both vocabularies, printed BEFORE the verdict is read (`RUN_RULES` A-11)

`SE = s / √n_eff`, where `s` is the **event-day abnormal-return dispersion measured on the arm's
own population** in the control pass (parameterised at **8pp** below purely to show the shape —
the executor substitutes the measured value). At crit **3.3145**:

| `n_eff` | SE (pp) | MDE 50% power | MDE 80% power |
|---|---|---|---|
| 400 | 0.40 | 1.33pp | **1.66pp** |
| 200 | 0.57 | 1.88pp | **2.35pp** |
| 100 | 0.80 | 2.65pp | **3.32pp** |
| 50 | 1.13 | 3.75pp | **4.70pp** |
| 25 | 1.60 | 5.30pp | **6.65pp** |
| 10 | 2.53 | 8.39pp | **10.51pp** |

**And the question that decides which row applies is not the event count — it is the
clustering.** Two readings, and the register must measure which is true rather than assume:

* **Pessimistic:** dips cluster in market-wide episodes, so `n_eff` ≈ the *episode* count. Over
  17.3 years that is single digits, and **at `n_eff` ≈ 10 the design needs a ~10pp mean abnormal
  return — larger than most single-name earnings reactions. Effectively dead.**
* **Optimistic, and probably right:** **earnings-day abnormal returns are idiosyncratic by
  construction** — reports are staggered across weeks, and the market-wide component on any one
  name's report date is small. If the within-episode residual correlation of *event-day* abnormal
  returns is low, `n_eff` approaches the event count.

**This is the technical reason event-timing helps beyond dilution: it converts a clustered
calendar exposure into a staggered, largely idiosyncratic one.** It is also an empirical claim,
so **control C6 measures the within-episode residual correlation and the power line is computed
from it** — not from the raw count and not from hope.

---

## 8. PRE-OUTCOME KILLS (own pass, read before the arm — `O10`'s process defect, not repeated)

* **K1 — THE `V6` FEASIBILITY KILL, and it can end the register for free.** From `V6`'s **banked**
  calendar-window statistics and the measured dispersion ratio `k = σ_e/σ_d`, derive the
  **implied event-time t** (§2's table). **If even that implied t falls short of the bar, the
  effect `V6` could not see does not clear when re-clocked either, and DC-1 STOPS — zero trials.**
  This is the strongest available kill because it tests the *premise of the whole register*
  rather than its hypothesis.
* **K2 — PEAD costume.** |mean per-date Spearman| of the DC-1 conditioning signal against banked
  `z_pead_car` **or** `z_pead_drift` > **0.60** → **WITHDRAWN.** Tested on both signed and
  absolute forms (`MB16`'s lesson: a registered kill statistic can be structurally blind to the
  renaming it exists to catch).
* **K3 — Δcomposite costume.** Same bar against `E-2`'s banked column.
* **K4 — VALUE costume.** Same bar against the value theme z-score, **plus** the mandatory
  descriptive report of the arm population's value-quintile distribution.
* **K5 — EPISODE concentration (`S10`'s lesson).** If **> 40%** of qualifying events fall inside
  a single market-wide episode, the arm may be reported **descriptively** but carries **no
  verdict** — it would be a description of one episode wearing a cross-sectional result's clothes.
* **K6 — the provenance pin.** NOW and CRM absent from the scoring path, by test (§0).

---

## 9. CONTROLS

**C1** stage-0 census banked and reproduced before the arm; the arm refuses without the artifact.
**C2** point-in-time: drawdown, flags and event date use only information available at entry;
an AST test asserts no forward column is loadable (`MB18`'s idiom). **C3** as-traded prices for
the drawdown, adjusted for returns, both pinned. **C4** the spine filtered to earnings, with the
IBES-vs-code-22 **disagreement rate reported** (`W-3b`: code 22 is broader than earnings).
**C5** the control population's composition reported beside the arm's (size, sector, value
quintile) so a composition effect cannot masquerade as the result (`MB1`'s menu-depth
convention). **C6** within-episode residual correlation of event-day abnormal returns — **the
power input**, measured not assumed.

---

## 10. VOID CONDITIONS

1. Quoting `V6-B`'s survival figure as return evidence, anywhere.
2. Sweeping the drawdown threshold, the flag count, or the event window.
3. Reading K1–K6 in the arm's pass.
4. Citing NOW or CRM as corroboration of the result.
5. Claiming the register "corrects" or supersedes `V6`.
6. Quoting the (B) secondary as an independent verdict.
7. Any adoption — this register measures.

---

## 11. PRIOR AND EXPECTATIONS, written before any run

**Prior: ~12% CONFIRMED.** Built down from a hostile record — `V6` four nulls, `E-2` null, PEAD
rejected, `MB18` rejected, the value costume near-structural, and a provenance that is selection
on the outcome — and built back up only by two things: **the clock argument is real and
quantified (2–4×), and the instruments genuinely did not exist when `V6` ran.**

Expectations to be scored: (1) K1 does **not** fire and the register proceeds — 55/45;
(2) K4 (value) is the kill most likely to fire — 45/55 against firing; (3) the verdict is NULL —
80/20; (4) the (A) jump arm shows a larger point estimate than the (B) drift arm — 70/30;
(5) the measured within-episode correlation is low enough that `n_eff` ≈ event count — 65/35;
(6) at least one number here contradicts this list — 60/40.

---

## 12. WHAT THIS REGISTER DOES NOT DO

It does not adopt, does not touch the composite or the shipped book, does not re-open `V6`, does
not license any product copy (`V3` still forbids per-name precision), does not make a claim about
NOW, CRM, or any named holding, and — **if K1 fires — it does not run at all, which is the
cheapest good outcome available to it.**
