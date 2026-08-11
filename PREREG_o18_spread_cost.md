# PRE-REGISTRATION — O18, the spread-conditional cost model

**Committed together with `PREREG_o10_passive_fills.md`, and ALONE, before any measurement code for
either item exists.** Ledger row `O18`, `src=auto`, *"no mention anywhere in the corpus"*.

The question: the options engine charges **one number** — the full quoted half-spread, at both
ends, via `DEFAULT_AGGRESSION = 1.0`. O18 asks whether cost is better described as a **function of
the observed spread state** than as a constant. O14's tick cache makes the effective spread
measurable for the first time.

**§0–§3 of `PREREG_o10_passive_fills.md` are incorporated by reference and are not restated:** the
same scope limits (alert-days only, zero D+1 coverage, zero exit-day coverage, entry leg only), the
same disclosed prior knowledge, the same eligible-print definition, the same
`SINGLE_LEG_CODES = (0, 18, 35, 95, 106)` primary with package-like codes excluded, the same
`MIN_PRINTS = 10`, the same contract-day unit, the same 2021-03-08 half split, the same
month-block bootstrap, and the same C1–C5 controls. **If O10's controls void, this item voids
with them.**

---

## §1 THE QUANTITY

For each eligible print: `mid = (bid+ask)/2`, `half = (ask-bid)/2`, and

* **quoted half-spread** `q = half`
* **effective half-spread** `x = |price - mid|`
* **the ratio** `ρ = x / q` — the fraction of the quoted half-spread that a real trade actually
  paid. `ρ = 1` is the engine's assumption. `ρ < 1` means the engine overcharges.

`ρ` is aggregated to the contract-day as a **size-weighted** mean (a cost model should be weighted
by the contracts that actually changed hands), then averaged equally across contract-days. The
**unweighted** version is reported alongside; if the two disagree in direction that is itself
reported, not reconciled away.

**Two spread levels, deliberately kept apart, because conflating them is the obvious error.**

* `q_print` — the quoted half-spread **prevailing when trades happened**.
* `q_eod` — the book's own `entry_spread_pct`, the EOD chain snapshot it actually charged.

§1 of the O10 register already records these differ on a 250-entry sample (**0.04066 vs 0.06250**
in spread-pct terms). **`q_print` is a selected quantity** — trades happen when the market is
there — so the gap between them is *not* evidence the engine is wrong by that amount. The
decomposition below keeps the two effects separate rather than letting them add up into one
flattering number:

```
total overcharge  =  ( q_eod - q_print )   +   ( q_print - x )
                     ^ availability          ^ price improvement
                     (selected: you only        (real: trades print
                      pay it if you trade        inside the quote)
                      when the market is there)
```

Only the second term is a property of execution. The first is reported and explicitly **not**
claimed as a saving.

---

## §2 THE CONDITIONING FAMILIES — SIX, FIXED, NO OTHERS

Each is cut into **quintiles** within the primary sample.

| # | family | rationale |
|---|---|---|
| F1 | quoted spread-pct `q_eod/mid` | the state the engine already measures |
| F2 | entry premium level | a $0.40 option and a $20 option are not one cost regime |
| F3 | DTE at entry | term structure of liquidity |
| F4 | market cap tier (`marketcap_musd`) | the book's own liquidity proxy |
| F5 | minutes from the open | intraday spread seasonality |
| F6 | print size | retail-sized vs institutional-sized executions |

`opt_right` and `horizon` are **not** families: the banked book is 100% calls and 100% `swing`
(O13), so both are degenerate and would be a fake arm.

---

## §3 THE STATISTIC AND ITS CALIBRATED NULL

**Dispersion:** `R_range = max_quintile(ρ) - min_quintile(ρ)` for each family. A single number
suffices iff `ρ` is flat across states.

**A raw `R_range` is not evidence of anything** — five quintile means of a noisy quantity differ by
chance, and this project has already recorded exactly that error once (R3, where a design effect
near 1.8 arose from pure sampling error). So `R_range` is scored against a **within-book label
permutation null**: hold every contract-day's measured `ρ` fixed, permute the quintile labels
within the book, recompute `R_range`. **2,000 draws, seed 20260811.** This preserves the marginal
distribution of `ρ` and the bin sizes exactly, and is the same instrument built for O13.

**Ordering:** Spearman correlation of `ρ` against the quintile index — a monotone cost function is
a usable model; a jagged one is noise even if its range is wide.

---

## §4 THE VERDICT RULE — FIXED BEFORE ANY NUMBER EXISTS

For each family, **SPREAD-CONDITIONAL IS WARRANTED** iff, **in both halves**:

1. `R_range > p95` of that family's own permutation null, **and**
2. the Spearman ordering agrees in **sign** across the two halves.

**Item-level verdict:**

* **WARRANTED** — at least one family clears both conditions in both halves.
* **NULL** — none does. The single-number model stands, and `ρ` is then reported as **one
  calibrated constant** with its interval, which is a useful result in its own right.

Ambiguity against a bar is a NULL (`RUN_RULES` A6).

**A family clearing on the full sample but not in both halves is REPORTED AND NOT ACTED ON.**
Session 7's leave-one-out pattern has now recurred five times in this project; the both-halves
requirement exists because of it.

**ROUTING, IDENTICAL TO O10 AND FIXED IN ADVANCE: nothing is adopted in this session.** No cost
constant is edited, no book re-banked, no published options figure re-stated. A WARRANTED verdict
is written up and **routed to Don**. `DEFAULT_AGGRESSION` stays 1.0 and a test will pin that it did
not move.

**THE MISREADING TO HEAD OFF, and it is the more dangerous one here.** If `ρ < 1` the engine
overcharges cost, so every options expectancy in the record is **understated**. That is *not* a
finding that the options signal works: R2's control pays the identical cost, so correcting the
cost line moves the alert book and its random-entry control together and leaves the −5.0640pp gap
untouched. The one place it genuinely matters is the **forward paper book's cost line**, which is
what this item is for.

---

## §5 EXPECTATIONS — WRITTEN DOWN FIRST

| # | expectation | confidence |
|---|---|---|
| E1 | `ρ < 1` on the full book (trades print inside the quote) | 80/20 (disclosed in O10 §1) |
| E2 | Item verdict is WARRANTED in ≥ 1 family | 70/30 |
| E3 | F1 (quoted spread-pct) has the largest `R_range` | 60/40 |
| E4 | `ρ` falls as the quoted spread widens — wide quotes are the least real | 70/30 |
| E5 | F5 (time of day) clears in both halves | 45/55 |
| E6 | Size-weighted and unweighted `ρ` agree in direction | 85/15 |

---

## §6 TRIAL COST

**6 options trials**, one per conditioning family. The `ρ` level itself, the decomposition, the
controls, the halves and the permutation null are charged at zero — they search nothing.

Options `N` **252 → 258** on top of O10's 4. **Equity `N` untouched at 155.**

---

## §7 VOID CONDITIONS

1. Any O10 control (C1–C5) voids.
2. Any change to the six families, the quintile cut, the `ρ` definition, the null construction, the
   seed, the draw count or the two verdict conditions after any outcome number has been read.
3. Adding a seventh family after seeing the first six.
4. Quoting the availability term as a saving.
