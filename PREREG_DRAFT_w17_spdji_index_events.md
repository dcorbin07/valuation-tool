# PREREG_DRAFT_w17_spdji_index_events.md — index add/delete in EVENT TIME, declared as a CLOSURE PURCHASE
## Frontier Scout draft, 2026-08-28. **BLIND. Zero trials charged by this file. No outcome statistic computed.**
## For an executor to accept or reject. **Rejection costs nothing.**

---

## §0 · THE UNUSUAL THING ABOUT THIS DRAFT: IT EXPECTS TO FAIL, AND SAYS SO ON ITS FACE

**This register's prior of finding an edge is LOW and the draft does not hide it.** The index
add/delete premium is the most-documented decayed anomaly in the equity literature; the honest
expectation is that whatever existed pre-2000 is gone.

**It is proposed anyway, for two reasons that are both structural rather than hopeful:**

1. **It lands in the highest-power space this record has.** `SEARCH_DOCTRINE` §1.4 measures the
   equity cross-section's 80%-power MDE at **0.4274 SD** — approximately equal to the largest
   anchor the panel has ever held (`z_fcf_margin`, **0.4346 SD**) — against **event time** at
   roughly **1.66pp at n_eff 400**. **An order of magnitude, on the same panel.** Index events are
   **exogenous, dated, and staggered**, which is exactly what event time requires.
2. **It is declared as a CLOSURE PURCHASE.** A powered null here **closes** the index-event thread
   — `OPTIONS_BRAINSTORM` #11 and #41, both previously blocked on reconstitution history — and
   closes it **by arithmetic rather than by a run of nulls**, which is the only kind of closure
   `SEARCH_DOCTRINE`'s standing rule calls durable.

> **Declared intent, pre-committed: a null verdict CLOSES this thread permanently.** The register
> may not be re-run later with a different window, a different index, or a different bar. If that
> pre-commitment is not acceptable to the executor, **reject the draft** — an unclosable register
> is not worth the trial.

---

## §1 · THE HYPOTHESIS AND THE ARM

**Hypothesis:** names added to (deleted from) a major S&P index earn abnormal returns around the
**announcement** date, in **event time**, net of the costs the record's own cost model charges.

**The arm:** cumulative abnormal return over a declared event window measured **from the
ANNOUNCEMENT date**, benchmarked against the shipped risk adjustment, on the full set of
add/delete events that intersect the panel's universe and dates.

**Arms declared, one gate:**

* **A1 · ADDS (gate).** CAR over the declared window, one statistic, one bar.
* **A2 · DELETES (reported, non-decisive).** Same construction. Deletes carry a survivorship
  hazard adds do not, and the draft will not gate on the dirtier population.

**Frozen before any data is pulled:** the event window in **sessions relative to announcement**;
the index set; the benchmark; the abnormal-return model. **No window may be chosen after seeing
dispersion** — a window selected on the outcome makes the verdict **VOID** (`MA55`'s free-parameter
rule).

---

## §2 · THE CLOCK IS THE WHOLE REGISTER — announcement, not effective

**`DC-1` established the clock argument for this project and it applies here with more force**,
because index events have **two** dates and the literature's entire effect lives between them.

* **Announcement date** — when the information arrives.
* **Effective date** — when index funds must trade.

**If the census supplies only EFFECTIVE dates, the event is mis-clocked and this register does not
run.** That is `K1`, it is free, and it is the most likely kill.

**And the arithmetic, from `DC-1` §7's form:** a calendar-window measurement of a point-mass event
payoff measures `J/(σ_d·√W)` where an event-window measurement measures `J/σ_e` — a gain of
`√W/k`. **The whole reason to run this in event time rather than as a panel column is that gain,
and it evaporates entirely if the clock is wrong.**

---

## §3 · GRAVEYARD, AND THE COSTUME CHECK

| row / prior | what it says | how this argues past it |
|---|---|---|
| **the decay literature** | the index effect has decayed toward zero since ~2000 | **not argued past — conceded.** This is why the register is declared a closure purchase, not a discovery |
| `OPTIONS_BRAINSTORM` #11 / #41 | previously **blocked on reconstitution history** | the block was **data**; width dissolves it. But dissolving a block is not evidence of an effect |
| **PEAD** | a dated-event drift family with a strong prior | index events are **not** earnings events; the register must show its window does not overlap earnings announcements, or condition on it. **Declared as an exclusion, before the arm** |
| `S15` / `S25` | sector-neutral is closed; PIT classification was the blocker | **unrelated object.** This register does not neutralise anything |
| **the SIZE costume** | index adds are large, deletes are small — an index-event effect can be a size effect wearing a costume | **`E-1` is the precedent, stated precisely:** its `K2` was a **correlation bar** — *"the graveyard aggregate is a SIZE SORT at mean per-date absolute rho **0.6114** against a **0.60** bar"* — and the arm never ran. **The lesson imported here is the SHAPE (a pre-outcome control that catches a size costume), not the specific statistic** |
| **the MOMENTUM costume** | adds follow price run-ups by construction | pre-event return is a **declared control**, stated before the arm |
| `MB12` | orthogonality is not a motivation | not claimed — this is an **event study**, not a composite column |

---

## §4 · THE KILLS — three free, and the first is the likeliest

| kill | fires when | cost | consequence |
|---|---|---|---|
| **K1 · CLOCK** | the census returns **effective dates only**, with no announcement date | **FREE** | STOP. The event is mis-clocked and §2's entire power argument evaporates |
| **K2 · EVENT COUNT** | the number of announcement events intersecting the panel's universe **and** its 2009–2026 dates falls below the `required_n` §5 computes | **FREE** | STOP and state the shortfall. **Do not run an underpowered event study** — `RUN_RULES` A-11 |
| **K3 · SIZE COSTUME** *(`E-1`'s shape, not its statistic)* | the effect does not survive a **within-size-decile** sort, declared as a leg before the arm | costs the arm, not a trial | the effect is a size effect wearing an index event's name. `E-1`'s own kill was a correlation bar at **0.6114 against 0.60**; this register uses a size-decile sort because the costume here is size **by construction** rather than by correlation |
| **K4 · CLUSTERING** | events cluster on a handful of reconstitution dates such that the effective number of independent events collapses toward the number of **reconstitution dates** rather than the number of **names** | **FREE** | **the most technically dangerous failure here.** S&P reconstitutions are batched; 400 events on 20 dates is **not** n = 400. Effective n is **measured, not assumed** |

**`K4` deserves its own sentence.** `SEARCH_DOCTRINE` §1.4 gives event time an n_eff in the
hundreds-to-thousands *"if within-episode residual correlation is low."* **Index reconstitutions
are the case where it is NOT low** — many names move on the same day, in the same direction, in
the same market. **The declaration must report the measured effective n, and if it collapses to
the reconstitution-date count, this register is running in the 69-date space it was designed to
escape.**

---

## §5 · POWER — MB22, at both vocabularies

**Object: an abnormal return in percentage points**, so the vocabulary is pp, not SD.

`crit = √(2·ln N)`. On the ledger-confirmed base of **242** (`WIDTH_AUDIT` §0.4), running fourth
this season puts **N = 247** at read → **crit = 3.319454** — **and that is exactly where `MB31`'s
seed-1003 floor at 3.319188 is crossed, so a bounded floor re-derivation is OWED with this
register.** The declaration re-reads the counter and says so on its face rather than discovering it.

* **`MDE_50% = crit × se_e`**
* **`MDE_80% = (crit + 0.84) × se_e`**
* **`required_n = ((crit + z_power)/effect)²`**

where **`se_e = σ_e / √n_eff`**, `σ_e` is the cross-event dispersion of the CAR and **`n_eff` is
the CLUSTER-ADJUSTED event count from `K4`, measured before the arm.**

**The reference point the declaration must state alongside its own numbers**, so the reader can
see whether the space is worth entering: `DC-1` §7 put event time at roughly **1.66pp at
n_eff = 400**. **At n_eff = 40 — one reconstitution date per quarter over ten years — the same
arithmetic gives roughly 3.16× that, and the register is no longer in a high-power space at all.**

> **This is the register's honest pivot point, and it is decided by `K4` before the arm:
> `n_eff` in the hundreds makes this the best-powered thing on the width map; `n_eff` in the tens
> makes it worse than the cross-section it was meant to escape.**

---

## §6 · DATA

**Tables the census must probe — and this is the entry with the LEAST confirmed about it:**

| what | what the census must return |
|---|---|
| the Historical SPDJI schema and tables | **the exact names** — the 2026-08-25 account probe did **not** enumerate an SPDJI library, so **existence is the first question**, not the second |
| membership records | index id, name identifier (`gvkey`? `cusip`? `permno`?), **`from` / `thru` dates** |
| **announcement dates** | **carried separately from effective dates — YES or NO.** `K1` turns on this single fact |
| index scope | S&P 500 only, or 400 / 600 as well — the mid- and small-cap indices carry more events and less liquidity |

**Standing assumption after W-14, W-16 and W-25:** *a product is absent until a `SELECT`
succeeds.* This register's very first census line is therefore **"does the library exist?"**, and
a negative answer costs nothing.

**Licensing fence:** WRDS is **research-only, never public**; raw rows never leave `D:\wrds`.

---

## §7 · TRIAL ACCOUNTING

**Zero trials by this draft.** **1 equity trial** if a CAR verdict is read. If run fourth this
season: N **246 → 247**, hurdle **3.318232 → 3.319454** (Δ **+0.001222**) — **and the `MB31` floor
re-derivation lands here.**
**Four kills fire first and three are free**, so the modal outcome is a **free stop at `K1` or
`K4`**.

---

## §8 · WHAT THIS BUYS EITHER WAY

* **A powered null** closes the index-event thread permanently and by arithmetic — the durable
  kind of closure — and takes `OPTIONS_BRAINSTORM` #11 and #41 with it.
* **`K1` or `K4` firing** costs nothing and still produces a **dated, named reason** the thread is
  unreachable, which is better than leaving it open as a maybe.
* **A positive result** would be the record's first event-time finding, and would immediately
  raise the value of every other staggered-event class the doctrine points at.

> **All three outcomes are worth having, and two of them are free. That is the case for the
> register — not a belief that the index effect survived.**
