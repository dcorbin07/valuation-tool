# PREREG — U6's OVERWRITE leg, re-opened on a corrected coverage number

**Committed ALONE, before any arm is scored.** One `.md`, zero `.py`; a strict git ancestor of
every measurement commit.

**TWO PARTS, AND ONLY THE SECOND IS A TRIAL.**

* **PART A — the coverage CORRECTION. ZERO TRIALS.** A fact about which set a published number
  was computed over. No hypothesis, no threshold, no verdict against a bar — the `S25` /
  `PT-WRITER` / `MA56` class. It lands whatever happens to Part B, because a ledger row that
  misstates its own blocker misleads every future reader of it.
* **PART B — the overwrite arm.** Registered here, **GATED ON P1 STAGE 0**
  (`PREREG_p1s0_optionable_gate.md`). If Stage 0 returns `CLOSED`, Part B does not run and
  charges nothing. See §5.

**ORDERING, STATED PLAINLY. Part A was MEASURED BEFORE this file was written; Part B has not been
touched.** Part A needs no pre-registration and by precedent would not get one — it tests no
hypothesis against no threshold, and `S25` and `PT-WRITER` both closed on exactly that basis with
no register at all. It is written up here rather than separately only because it is the reason
Part B exists, and a reader who found the correction without the arm beside it would have to
guess what follows from it. **Part B's arm, bars and verdict rule are genuinely blind: no
overwrite has been priced, no premium collected, and no comparison run, at the time of this
commit.** That is the claim that matters and it is the one a later reader can check against the
history.

---

## 0. PART A — the blocker is wrong, and NOT for the reason the re-open was premised on

### 0a. What the row says

`VALQUO_LEDGER.md` closes `U6` **`DESIGN-RECORDED / NOT BUILDABLE ON DATA WE OWN`** on one
measured number, quoted verbatim from the row:

> *"of 7,132 names **ENTERING** the top decile across 68 transitions only 129 have mined chains
> = **1.81%** … a MEDIAN OF 2 covered names in a book whose mean top-decile size is 165.6, with
> ZERO covered entries on 18 of 68 dates"* — and, decisively, *"measured on the corrected
> 69-date panel **against the 187-name mined universe**"*.

### 0b. Two controls first, so the comparison is like-for-like rather than merely similar

Before any correction is claimed, the instrument is shown to be measuring the same objects:

| control | published elsewhere | measured here | agreement |
|---|---|---|---|
| top-decile **entry** events across the panel | **7,132** (U6 row) | **7,138** | 6 events, **0.08%** |
| top-decile **membership** rows across 69 dates | **11,426** (`S10`, and `V6-B`'s C7 independently) | **11,426** | **exact** |

The membership count reproducing **exactly** is what establishes that "top decile" here is the
same object every published top-decile figure describes — it uses the shipped
`argsort(-composite)` split into ten buckets, not a re-derivation that happens to agree.

### 0c. THE CORRECTION IS THE UNIVERSE, NOT THE LEG — and the leg runs the OTHER WAY

The re-open was proposed on the ground that the blocker measured **entries** while an overwrite
is written on **holdings**. **That premise is refuted by measurement.** On the identical
all-transitions denominator, point-in-time:

| set | covered | total | share |
|---|---|---|---|
| **entries**, any point-in-time chain | 648 | 7,138 | **9.08%** |
| **entries**, chain + O20's liquidity screen | 371 | 7,138 | 5.20% |
| **holdings**, any point-in-time chain | 897 | 11,426 | **7.85%** |
| **holdings**, chain + O20's screen | 504 | 11,426 | 4.41% |

**Holdings are 0.86× as well covered as entries, not the 6–11× the re-open assumed.** The two
legs sit within about one percentage point of each other, and if anything the overwrite leg is
the *worse* covered of the two.

**What is actually wrong with the 1.81% is its DENOMINATOR OF NAMES.** It was measured against
the **187-name alert universe** — the universe the options *alert* book was built from — while
the chain cache holds **1,000 ticker directories, 906 of them names in the equity panel**. That
is a **4.84×** larger name set, and it produces a **5.02×** larger coverage figure
(1.81% → 9.08%). The two ratios agreeing to within 4% is the evidence that the universe is the
whole explanation.

**AND THE CORRECTION IS UNDERSTATED, because it runs against a STRICTER test.** The row's
measure asks whether a ticker *has mined chains at all*; this one asks whether a chain exists
**on that very date** and (for the primary) whether the miner's own screen passes on it. A
point-in-time test can only ever be smaller. It is 5× larger anyway.

*(A reconciliation, reported rather than smoothed over: the row records "ZERO covered entries on
18 of 68 dates" and this measures **28**. The 28 are exactly the pre-2016 dates, where the cache
holds nothing at all. A non-dated membership test can score a pre-2016 entry as "covered"
because the ticker is mined in some later year, which is how the row reached a smaller count on
a smaller universe. The two numbers are not comparable and neither is wrong on its own terms.)*

### 0d. WHAT THE CORRECTED NUMBER DOES AND DOES NOT UNBLOCK

**It does not unblock the CSP entry leg**, which is untouched and remains coverage-bound.
**It does establish that the overwrite leg is buildable**: on the 40 covered dates the median
top-decile book holds **169.5 names, of which 12 are PIT-liquid and 21 have any chain**, and
**ZERO covered dates have zero optionable holdings** — so there is no date on which the
overwrite is impossible, which is the specific thing the row's "median of 2, zero on 18 dates"
asserts.

**AND IT IS BOUNDED, WHICH IS THE SENTENCE THAT MATTERS MORE THAN THE UNBLOCKING.** An overwrite
that can only be written on **7.3% (PIT-liquid) to 13.0% (any chain)** of decile slots can only
move the book by that fraction of whatever it does to the names it touches. §3's power clause
turns that into a number **before** the arm runs, and if the largest arithmetically possible
effect sits below the design's own MDE then this leg is **UNANSWERABLE on owned data** and the
honest action is to say so and charge nothing — the session-8 `SELRULE` precedent, where
declining a test that could not resolve was the cheaper action rather than the lazier one.

---

## 1. THE PRIOR, STATED FIRST AND PLAINLY — I EXPECT THIS ARM TO FAIL

Writing a call on a name you hold **because it is rising** caps the upside that IS the edge.
This is not a hedge against the strategy; it is a sale of the strategy's own payoff.

The project has already measured the thing that makes it bite: **`S22` found top-decile alpha
still accruing at TWO YEARS** — cumulative +10.20% at 504 days, alpha HAC *t* 3.83 at the
longest horizon, every one of eight incremental quarters positive. So a call written on a
top-decile holding is written on a population whose forward return is **measurably not zero**.
U6's own design memo says exactly this, and it is the reason the row was never merely a
coverage problem.

**PREDICTION, WRITTEN BEFORE THE RUN: the overwrite REDUCES cumulative alpha by more than the
premium it collects, at 70/30.** The 30 is `O25`'s only comfort — that the 25-delta wing is the
expensive end of the surface (§2b of the frontier: 10.00% of premium at δ 0.0–0.2 against 1.79%
deep-ITM), so selling it is at least selling the costly thing rather than buying it.

Two further priors, both unfavourable and both recorded so a positive result has to survive them:

* **`O25` is the direct prior and it is hostile.** Rolling the wing was *reliably worse* than
  closing or holding — **−9.34pp at +75% and −13.03pp at +100%**, negative in **both halves**
  against **both** comparators, every CI excluding zero. O25 is short-dated and post-move so it
  is **not this arm**, but it is the nearest measured thing to it.
* **The buy-write premium is a documented risk transfer, not an anomaly.** Unlike the deep-ITM
  financing case (Frazzini–Pedersen's leverage constraint, with a named constrained
  counterparty), **I cannot name anyone who must sell this to us.** That asymmetry is why this
  register expects failure and the P1 one does not.

---

## 2. THE ARM — ONE, AND IT TARGETS MONEYNESS

**A1 — write a call against each PIT-liquid top-decile holding, roll quarterly, hold to expiry
or roll, no discretionary exit** (every exit rule is dead per `O1`/`O23`; the absence of one is
not a variant of one).

**STRIKE IS SET BY MONEYNESS, NOT DELTA, AND THIS IS THE ONE DESIGN CHOICE THAT IS NOT FREE.**
`V6-OPT` is the precedent and it is decisive: selling a 25-**delta** put is selling a 25%
assignment probability **by construction**, so a delta-targeted strike had *already spent* the
risk difference the trade existed to exploit, and its healthy/unhealthy arms came back 0.43pp
apart. A delta target is blind to a priced difference; a **moneyness** target is not. V6-OPT
named this as the obvious re-opening in as many words. **Strike = the listed strike nearest
1.10 × spot; DTE nearest 45.** A delta-targeted variant is a **void condition**, not an
alternative.

**Settlement:** on the derived layer's own as-traded `spot`. The adjusted close is used **only**
for the stock control's return. This trap has bitten `U1-SPLIT`, `O7` and `V6-OPT` — three
times — and it is pinned rather than remembered.

---

## 3. CONTROLS — and the power clause runs FIRST and can end the register

* **C-POWER (GATING, and it runs before any arm).** The largest arithmetically possible effect:
  overwrite share × (premium collected − upside forgone), bounded above by simply
  **premium × share** with zero forgone upside. Against the MDE of a paired within-panel
  difference on 40 covered dates, computed from the same `fixed_weights_null` machinery Stage 0
  uses. **If the maximum possible effect is below the MDE, the arm DOES NOT RUN, the leg is
  recorded UNANSWERABLE-ON-OWNED-DATA, and zero trials are charged.** `V2G` established there is
  no calibrated floor for a paired within-panel difference, so the 2.0 used here is
  **conventional and labelled uncalibrated** everywhere it appears.
* **C-BOOK (primary comparator).** The **un-overwritten** stock book on the identical names and
  dates. The arm must beat *itself without the overwrite*, paired — not beat a benchmark.
* **C-RANDOM.** A random-name overwrite matched per date on count and market-cap tier,
  **≥5 seeds pooled**. `R2`'s standing rule: five seeds minimum, and the paired name-year sign
  test carries the verdict, because a single seed can flip it on a barbell payoff.
* **C-HALVES.** Both halves of the covered subsample, boundary embargoed at the geometry Stage 0
  lands on. A full-panel gate is **impossible** here, not merely weak (29 of 69 dates hold no
  chain) — `S18`/`U2`/`U3`/`V6-OPT`/`MA31`, now the sixth time.
* **C-QUOTE.** Every written call must have a **two-sided quote** on the day it is written.
  `MA31` measured that pair-level two-sided availability is roughly the **square** of the
  leg-level rate; a single leg is better placed than a pair, but it is not free and the
  retention is reported.
* **C-FILL.** The shipped fill engine at `DEFAULT_AGGRESSION = 1.0` (sell the bid, never the
  mid). `O18` measured real trades printing at ρ **0.6743** of the quoted half-spread, so this
  is conservative — and O18's own register forbids quoting its 0.0545 availability term as a
  saving.
* **C-ASSIGN.** Assignment is settled on the as-traded spot, and an assigned name **leaves the
  book** rather than being silently re-bought. Quietly re-buying would manufacture the exact
  upside the overwrite just sold.

---

## 4. VERDICT

**ADOPT-ELIGIBLE** requires, on the primary comparator: cumulative H=252 alpha **not reduced**
beyond the premium collected, in **both** halves, **and** the arm beating the ≥5-seed random
overwrite on the paired sign test. Anything else is **REJECTED**.

**Ambiguous against a pre-committed threshold is a NULL** (`RUN_RULES` A6). **ADOPTS NOTHING in
any case** — an overwrite on the live book is a construction change and a **vintage event**,
which is Don's call and not this register's.

---

## 5. GATING, TRIALS, AND VOID CONDITIONS

**PART B IS GATED ON P1 STAGE 0.** If Stage 0's family verdict is `CLOSED`, Part B does not run
and charges nothing; the frontier's §6 names this row as one of the six items Stage 0 gates, and
running an overwrite on a book whose composite does not sort its own optionable universe would
be measuring a book that is not there. If Stage 0 is `PARTIAL`, Part B may run and **must carry
the PARTIAL label**.

**TRIALS.** Part A: **zero**. Part B: **1 options trial** if it runs (one arm), options
`N` 292 → 293. C-POWER charges nothing whether it passes or refuses.

**VOID CONDITIONS.**

1. This file is not a strict ancestor of every measurement commit.
2. A threshold, the strike rule, the comparator or the verdict rule above is edited after a
   number is read. Corrections go in the write-up; the register is left unedited.
3. **The strike is targeted on DELTA rather than moneyness** (§2), or a second strike/DTE pair
   is scored. The grid is one arm and nothing else — sweeping moneyness until one clears is
   exactly what this forbids.
4. C-POWER refuses and the arm is run anyway.
5. Part A's coverage correction is reported as evidence that U6 is *tradeable*. It is evidence
   about **buildability of one leg** and nothing else.
6. The CSP entry leg is described as unblocked. It is not, and nothing here touches it.
