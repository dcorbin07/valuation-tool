# PREREG DRAFT — the event-ownership (EO) re-open rubric, written BLIND
## Which options-book verdicts may be re-read by earnings-spanning stratum, decided before any stratified number exists

**DRAFT, Frontier Scout lane, written 2026-08-20 while the EO register is IN FLIGHT and no
stratified re-read of any options-book row exists anywhere in the record.** The git history is
the blindness proof: this file's commit predates the EO register's landing commit, and every
classification below is argued from mechanism and from already-published pooled facts only.
`OPT-REOPEN` is the precedent and the template — *"a re-open list written after the new numbers
are visible is a list of the results someone liked"* — and this rubric is its EO-specific
successor, written for the same reason at the same kind of moment.

**Honesty note on what I have seen (so blindness is a checkable claim, not a vibe):** the
pooled book facts cited below, all previously published (`O11`'s crowded-week split, `O10`'s
liquidity split, `O13`'s within-bin decomposition, `MB3`'s spanning-vs-not terminal-wealth
arithmetic and its +10.30%/+5.50% control comparison, `O17C4`'s within-stratum entry result).
**No per-verdict stratified re-read exists and none has been seen.** If one lands before this
file, this draft is void and says so here.

---

## 0. What this rubric is for

If EO **confirms** (the in-flight register clears its own bars), every options-book verdict that
**pooled** spanning and non-spanning trades becomes a candidate for stratified re-reading — and
the moment the first stratified table exists, any list of "which rows deserve a second look"
can be written to flatter it. This file fixes the list **now**. If EO comes back **null**, §4
closes the rubric at zero cost and nothing is re-opened.

**The standing re-open rule binds:** a re-open needs new data, a new instrument, or a new
design. A confirmed EO flag is a **new instrument** (a validated partition of the same trades).
This rubric assigns each row to exactly one bucket:

* **EO-SENSITIVE** — a mechanism for interaction exists AND the stratified arithmetic can
  resolve it → eligible for a stratified re-read under §3's charging rule.
* **EO-INSENSITIVE** — already stratified by construction, already answered within-stratum, or
  closed on a mechanism a partition cannot move → not eligible; re-proposing one of these must
  cite this file against itself.
* **UNPOWERED-IF-STRATIFIED** — interaction mechanism may exist but the MB22 arithmetic forbids
  an interpretable stratified verdict → not eligible; recorded so nobody pays to learn it.

**Precedence rule, fixed now:** power beats mechanism. A row with a beautiful interaction story
and impossible arithmetic goes in bucket 3, and the story is noted, not honoured.

## 1. The stratum and the arithmetic (MB22 form, parametric on purpose)

The EO flag partitions the 3,885-trade alert book (3,870 split-clean) into spanning share `s`
and non-spanning `1−s`. **I do not know `s` and have deliberately not computed it** — the
executor prints it from the banked flag before any re-read. The arithmetic that governs every
bucket-3 assignment:

* A stratified statistic's SE inflates by **≥ 1/√s** on the spanning cell (more, once name-year
  clustering — `R3`'s deff ≈ 2.2 — concentrates: event trades cluster in earnings months).
* The 50%-power MDE inflates by the same factor; the **80%-power MDE is 1.42× the 50% figure**
  (`MB22`'s correction — the record's historical "MDEs" are all 50% figures).
* Worked reference rows, at pooled SEs already on the record:

| pooled SE (source) | s = 0.5 | s = 0.3 | s = 0.2 |
|---|---|---|---|
| flow-feature monthly sort, SE ≈ 4.82pp (`MB16`, banked) | 50%: 13.6pp / 80%: 19.4pp | 50%: 17.6pp / 80%: 25.0pp | 50%: 21.6pp / 80%: 30.6pp |
| per-trade expectancy, SE such that pooled 50%-MDE ≈ 3pp | 4.2pp / 6.0pp | 5.5pp / 7.8pp | 6.7pp / 9.5pp |

(Cells are `pooled-MDE × 1/√s` and `× 1.42` on top; the executor recomputes exact values from
banked SEs via `power_gate.state()` — the table's job is to show the shape, and the shape is
brutal: **at s ≈ 0.3 nothing whose pooled effect was single-digit pp is resolvable in the
spanning cell at 80% power.**)

## 2. Charging rule for stratified re-reads, fixed before anyone wants one

Re-grouping **banked per-trade rows** by the EO flag and quoting stratum means with cluster CIs
— no new arm, no new threshold, no new data — is a re-measurement on a new instrument and is
charged **1 options trial per grouped family** (the `MA26-A`/`MA28`/`MA54-1` one-hypothesis-
one-trial collapse precedent), families as listed in §3. Anything that adds an arm, a
threshold, or a rule is a new register at its own price. Nothing in this rubric licenses a
trade; `O11` binds everything.

## 3. The classification — every options-book verdict, one bucket each

### Bucket 1 — EO-SENSITIVE (eligible if EO confirms; priority order; families bracketed)

1. **`O11` — portfolio/concurrency (family: SIZING-A).** The strongest EO-adjacent pooled fact
   in the book: expectancy **−4.51% in quiet weeks, +14.28% above the 90th-percentile week**,
   51.5% of trades in >10-alert weeks. Mechanism: alert crowding plausibly *is* earnings
   season, so the cap refuses event weeks specifically. A spanning×crowding cross-tab of
   banked rows is the single cheapest EO re-read and reuses `MB3`'s wealth arithmetic.
2. **`O1` / `O23` / `O25` — exits (family: EXITS).** `O23` measured ~half of any exit rule's
   P&L difference is the underlying over the holding period; an announcement inside the window
   concentrates exactly that variance at a known date. Exit rules scored pooled may be
   averaging a pre-event regime with a post-event one. (`PATHSTUDY`'s 13 arms joined this
   family's pooled verdicts; it re-reads with them, not separately.)
3. **`O13` — anti-signal decomposition (family: DECOMP).** Its finding — the loss is a
   within-bin **rate** effect, −4.2 to −5.8pp everywhere — never asked whether "within every
   bin" survives the one partition with a mechanism. If the rate effect concentrates in
   non-spanning trades, `MB3`'s ownership story and `O13`'s decomposition become one story.
4. **`MB1`'s day-effect residual (family: DECOMP).** The −4.76pp DAY component of the pick gap
   was never located in time. Whether "bad days" are disproportionately non-spanning days is a
   regroup of banked menu legs. (`MB1-SEL`'s own outcome governs whether any selection-side
   number is quotable — the day side is unaffected by that gate.)
5. **`O18` / `O10` — spread and fills (family: COSTS).** ρ = 0.6743 was measured pooled;
   spreads widen into announcements mechanically. A stratified ρ changes every cost-adjusted
   number's error bar, which is an instrument correction rather than a verdict flip — cheap
   and worth it if EO confirms.
6. **`O12` / `O22` — Kelly/ruin and capacity (family: SIZING-B).** Tail concentration at
   events moves `f*` and depth. Sensitive by mechanism; only worth charging after family
   SIZING-A confirms structure, and §1's arithmetic must be printed per cell first.
7. **`MA31` / `MA32` — parity deviation, open/close share (family: FLOW-INFORMED).** The
   literature both items imported is explicitly about informed trading around announcements;
   both pooled. **Flagged sensitive with a hostile power note:** both were NULL-and-
   uninterpretable pooled, so §1's precedence rule likely lands them in bucket 3 once `s` is
   printed — the executor decides with the number, not the story.

### Bucket 2 — EO-INSENSITIVE (not eligible; citing this list is mandatory in any attempt)

* **`O6`, `O7`, `O17`, `O17C4`** — already event-conditioned by construction; `O17C4` is the
  **template**: it re-asked the entry question *within* the spanning stratum and was REJECTED
  on its own c3; that is what "already answered within-stratum" means. **`R2`'s headline
  therefore does not re-open on EO** — its within-stratum successor already ran.
* **`O24`** — the earnings-calendar question, asked directly and answered NO (R² CI wholly
  below the committed bar). The stratification-defining question cannot itself re-open.
* **`O9`, `A3`-class short vol, `V6-OPT`** — closed on a mechanism no partition moves: the
  delta-targeted strike spends the priced risk difference by construction. An EO stratum
  changes which days you sell; it does not change what the strike already sold.
* **`U1`** — every decile's median trade sits between −52.5% and −54.3%; a partition of a
  distribution with that shape relabels the loss, it does not relocate it. Failed four of four
  pre-registered conditions.
* **`U3`** (index-level overlay), **`O8`** (index VRP) — the announcement is single-name; the
  index object has no stratum.
* **`P1S0` / `P1S0-CONTROL`** — equity-sorting on the optionable universe; not an options-book
  pooling. The family stays closed at its power anchor.
* **`DEEPITM-FIN`** — a cost-of-carry measurement; the roll calendar does not know earnings.
  (Holding *through* events at long tenor is `O-SEED-4`'s new register, not a re-read.)
* **`R3`, `O19`, `O20`, `O15`, `O16`, `R7`, `MB15` (void), `OPT-REOPEN` itself** — instruments,
  artefact checks, mining scope, and a void row: nothing to stratify.
* **`O21` / `O21-D2`** — dividend mechanics; ex-div dates, not announcement dates, and the
  full CI already sat inside the materiality bar. A stratum cannot move a bound that tight.

### Bucket 3 — UNPOWERED-IF-STRATIFIED (mechanism noted, arithmetic decides)

* **`O14` (all five arms) and `MB16` (VPIN)** — pre-announcement informed flow is the
  literature's own window, so the mechanism is real. But `MB16`'s pooled 80%-power MDE
  (≈13.7pp) already exceeded its observed 8.35pp; at s ≤ 0.5 the spanning-cell 80% MDE is
  ≥19pp against effects that have never exceeded 9pp on this cache. Dead on arithmetic, and
  the alert-days-only conditioning caveat compounds it.
* **`O3` / `O4` / `O5`** — `O4` missed its own p95 by **0.0086** pooled; stratification
  inflates the bar's distance faster than any plausible stratum effect. Same for `O5`'s
  margin structure.
* **`O26`** — the per-bucket floor study: halving bucket occupancy breaks the floor the study
  exists to set; a stratified `P_flip` is arithmetic against itself.
* **`U7`** — veto lift CIs straddled zero pooled on 98% coverage; halved cells widen them past
  any reading.

## 4. Trigger table — what activates what, fixed now

| EO outcome | action |
|---|---|
| **CONFIRMS on its own bars, both halves** | Bucket-1 families become eligible in the listed order; SIZING-A first (regroup only, 1 trial); each further family charges per §2 and must print §1's arithmetic per cell before running. |
| **CONFIRMS on one half / mixed** | Only SIZING-A eligible (its regroup is the cheapest disambiguation); everything else stays shut pending a second EO-consistent result. |
| **NULL or UNINTERPRETABLE** | This rubric **closes itself**: no row re-opens, bucket assignments stand as the record that the list predates the numbers, and the file may not be edited (§5). |

## 5. Void conditions

1. Editing this file after the EO register lands — corrections go in a dated addendum below a
   horizontal rule, never in place.
2. Quoting this rubric as evidence that any pooled verdict is *wrong* — eligibility is not a
   finding.
3. Running any stratified re-read without its §2 charge booked first.
4. Reading a bucket-3 assignment as NULL — it is "invisible at this resolution," and the row
   says so.
5. Using the EO flag itself as an entry signal anywhere — that is a new register in a family
   with standing closures (`R2`, `O17C4`), not a re-read.

## 6. Expectations, written now, scored when EO lands

1. EO confirms on at least one half — **60/40** (the `MB3` control arithmetic points that way;
   the record's base rate points against).
2. If EO confirms, SIZING-A's regroup shows the crowded-week effect is substantially a
   spanning effect — **55/45**.
3. No bucket-2 row is ever legitimately re-opened on EO evidence — **85/15**.
4. At least one bucket-1 family, once its cell arithmetic is printed, moves itself to
   bucket 3 — **70/30** (`MA31`/`MA32` are the named candidates).
5. Don asks for exactly the re-read this rubric prices cheapest (SIZING-A) — **60/40**.
