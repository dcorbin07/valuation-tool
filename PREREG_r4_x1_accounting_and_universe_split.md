# PRE-REGISTRATION — R4 (multiple-testing accounting) + X1 (split on universe, not time)

**Registered 2026-08-13, blind.** Committed **ALONE** — one `.md`, zero `.py` — and a strict git
ancestor of every commit that measures anything.

**Two audit rows, one register. R4 is an ACCOUNTING audit charged to `infra`; X1 is a RETURN
hypothesis charged to `equity`.**

---

## 0. Premise findings — measured BEFORE this register, and one of them is the headline

Every number in this section is read off already-shipped fields or already-committed source. **No
new search over the data was run before this file was committed.**

### 0a. R4's four method bullets, audited against what M1 actually shipped

R4 (`VALQUO_EDGE_AUDIT.md:478-490`) prescribes four things. **Two are delivered, one is absent, one
is half-built:**

| # | R4's method | status | evidence |
|---|---|---|---|
| 1 | *"Build a single append-only research log"* | **DELIVERED** | `RESEARCH_LOG.md` + `research_log.py`; **121 rows, 521 trials logged** |
| 2 | *"Feed the real `N` into the Deflated Sharpe"* | **DELIVERED** | `n_trials 218`, `n_trials_source: "RESEARCH_LOG.md (audit M1)"`, `is_effectively_undeflated: false` |
| 3 | *"Apply Benjamini–Hochberg across the family of **equity** signal tests"* | **ABSENT** | BH exists **only in the options lane** — `tickflow_signals.benjamini_hochberg`, `s17_event_codes`'s own copy, `path_gate`. **Nothing applies it to an equity family.** |
| 4 | *"Report the Harvey–Liu–Zhu adjusted hurdle"* | **HALF-BUILT** | `_trials_haircut` computes √(2·ln N) and the CPCV adopt gate **uses** it — but the artifact contains no `harvey`, `hlz` or `hurdle` string, and **nothing anywhere compares the HEADLINE against it** |

### 0b. THE FINDING BULLET 4 WAS SUPPOSED TO SURFACE AND NEVER DID — AND IT REFUTES R4's OWN EXPECTATION

R4's *"What this buys"* paragraph says: *"the long-short **t** of 3.52 **probably clears** a
properly-computed hurdle, which is a much stronger claim than the current one **because** it is
defensible."*

**Two shipped numbers, no new computation:**

* headline long-short **HAC *t* = 2.6199121240414884**
* Harvey–Liu–Zhu hurdle at the honest denominator, **√(2·ln 218) = 3.2816139513322065**

**2.6199 < 3.2816. THE HEADLINE DOES NOT CLEAR THE HLZ HURDLE, AND MISSES BY 0.66 OF A *t*.**
R4's 3.52 was the **pre-B6 void panel**; the corrected figure is 2.62, and `N` has gone 8 → 218 in
the meantime, so the hurdle rose while the statistic fell. **Both movements run against the claim.**

**THE COUNTER-ARGUMENT IS REAL AND IS REGISTERED HERE RATHER THAN DISCOVERED LATER, BECAUSE IT
DECIDES HOW THIS MUST BE REPORTED.** The HLZ hurdle prices *the best of N draws*. **The shipped
composite is not the best of anything** — it is flat 1/7, never tuned, and `cpcv.adopt` is `false`
on every run, so the 218 trials are overwhelmingly **rejected alternatives to it** rather than
candidates it won against. And **X7's empirically CALIBRATED long-short HAC floor is 2.2837, which
the headline DOES clear.**

**So the project clears the bar measured against its own placebo and fails the bar derived from
counting its own trials. That tension IS R4's residual, and §2.3 fixes in advance that both numbers
ship side by side and neither is presented as "the" answer.**

### 0c. The two items the task named

* **The infra-vs-search charging convention: DELIVERED, documented AND enforced in code.**
  `RESEARCH_LOG.md:57` — *"`FIXED` marks a correctness repair rather than a hypothesis test.
  `FIXED` rows do NOT count"* — and `research_log.py:23` restates it. **29 rows are currently
  `FIXED`-and-not-counted.** The `counting_rule` field ships the sentence. **Nothing to close.**
* **Family-wise accounting across lanes: A GAP, and it is structural.** `research_log.DOMAINS`
  declares **four** domains — `equity`, `options`, `unified`, `infra` — and **`unified` reads
  ZERO**. Every U-series item (U1–U8), which tested explicitly *unified* equity-plus-options
  hypotheses, was charged to `equity` or `options`. **So there is no cross-lane family; there are
  three parallel single-lane families and one declared-but-dead bucket.** Today: equity **218**,
  options **292**, unified **0**, infra **11**.

### 0d. A number worth recording in its own right

`gap_to_audit_estimate` is **−375**: the audit estimated ~146 trials and the log has now
recorded **521**. **The project has run three and a half times the searches the audit assumed when
it wrote R4.**

### 0e. X1's spec, and the one way it must be simplified

`VALQUO_EDGE_AUDIT.md:1723-1733` asks to *"randomly partition the ~2,710 names into two halves by a
stable key — a hash of the ticker… Make every decision on half A. Measure on half B,"* and calls it
*"possibly the highest-value methodological change in the document."*

**THE "DECIDE ON A, MEASURE ON B" HALF CANNOT BIND HERE, AND SAYING SO IS NOT A DODGE.** The
deployed strategy **fits nothing**: flat 1/7 weights, never tuned, and CPCV declines to adopt on
every run. There is no decision to leak. **So X1 on the headline reduces to "measure on both
halves", and what it tests is GENERALISATION ACROSS NAMES — not decision leakage, because there is
no decision.** That is the honest scope and it is fixed here before any result.

**Everything X1 needs is already banked**: `panel_r5r6.pkl`, 69 dates, 2,531 names, 113,945 rows,
and it reproduced the record bit-identically under R5+R6's own C1 hours ago. **No panel rebuild.**

---

## 1. R4 — what this register closes, and what it cannot

### 1.1 Closable now

**Bullet 3 — BH across the equity signal family.** The audit's own analogue is explicit: *"as the
options autopsy already does for its **126 features**."* **Features, not log rows** — and that
matters, because `RESEARCH_LOG.md` records verdicts and **has no p-value column**, so BH is *not*
computable across the log and never was. It **is** computable across the **per-signal IC table**,
which is the equity analogue of the autopsy's 126 features: **53 registered numbers**, each with a
per-date IC series and a *t*.

Applied at **q = 0.05**, two-sided, on the banked panel. **Reported for both the shipped `ic_tstat`
and the HAC `ic_inference.t`**, because M2 made the second the clustered default and the two answer
slightly different questions.

**Bullet 4 — the HLZ hurdle, reported rather than only used.** §0b's comparison ships as a named
block so it cannot go unread again, carrying **the statistic, the hurdle, the calibrated X7 floor,
and the §0b counter-argument in the payload itself.**

### 1.2 Not closable, and named

* **BH across the LOG is impossible without a p-value column.** Adding one retrospectively would
  mean reconstructing a *p* for 121 heterogeneous rows measured against different statistics on
  different universes — **an invention, not a measurement.** Recorded as R4's permanent residual.
* **The `unified` domain (§0c)** is a reporting gap this register **measures and routes**; deciding
  whether cross-lane claims need their own denominator is a methodology change with consequences
  for every published `N`, and it is **not made here.**

### 1.3 Verdict rule for R4, fixed now

> **R4 closes `DONE` iff bullets 3 and 4 are both delivered in this session.** Otherwise it closes
> **`SUPERSEDED-BY-M1`** with the residual named. **Either way the residual list of §1.2 is
> published**, and the row records that **R5's own row already leaned on R4's note as routing
> input**, so anything R4 leaves open is load-bearing elsewhere.

**R4 is charged to `infra`, not `equity`** — it is accounting over existing measurements and
searches no new data. **Applying BH to already-charged tests is a CORRECTION, not a new search**,
and charging it to `equity` would double-count the very trials it is correcting. M2/M6/S28's
precedent: infra rows carry `n=1` and **infra `N` gates no published claim.**

---

## 2. X1 — the universe split

### 2.1 Construction

**Panel:** the banked `panel_r5r6.pkl`. **Weights:** the deployed flat 1/7 over the seven scored
themes. **Statistic:** the shipped `quantile_backtest` at `n_q=10, horizon=63` — the same function
the headline comes from.

**Two split families, and the first is the audit's own:**

1. **THE STABLE-KEY SPLIT (primary).** `int(sha1(ticker).hexdigest(), 16) % 2` — deterministic,
   carries no seed, and **reproducible by anyone with the ticker list**, which is what the audit
   meant by *"a stable key."*
2. **THE RANDOM-SPLIT DISTRIBUTION.** `K = 100` seeded 50/50 partitions, so the primary split is
   placed in its own sampling distribution instead of being one draw quoted alone.

### 2.2 The bar is calibrated ON HALF BOOKS — X7's floors are an extrapolation here and are labelled one

A half universe is ~1,265 names, so a decile holds ~126 rather than ~253. **X7's 2.2837 and 1.95pp
were calibrated on the full-universe decile book and do not transfer to an object of half the
size.** Quoting them as the bar would be the uncalibrated extrapolation X3 and session 10 both paid
for.

**So the null is rebuilt for this object:** `J = 200` draws, each a **random half** whose theme
columns are then shuffled within date by the shipped **`placebo_panel`** and re-scored through the
same `quantile_backtest`. Composites are **recomputed** from the shuffled columns, which is why
this is a real null and not the invariant one — the recorded failure mode is pointing a permutation
at an **already-computed** score column. **p95 of that distribution is the bar**, for alpha and for
long-short HAC *t* separately. Every draw banked.

### 2.3 Verdict rule, fixed now — two arms, each with its own

> **A1 (top-decile alpha) SURVIVES** iff **all three** hold:
> **(a)** on the **stable-key** split, **both** halves are positive **and** both clear the
> half-universe alpha p95;
> **(b)** across the 100 random splits, **≥ 80%** of the 200 half-books clear that p95;
> **(c)** **both** halves clear in **≥ 64%** of splits.
>
> **A2 (long-short HAC *t*) SURVIVES** on the same three-part rule against its own p95.

**(c) is derived, not chosen: 0.64 = 0.80².** It is exactly what independence would predict from
the marginal rate in (b), so the joint condition **adds no demand beyond (b) being met** and cannot
be tuned to flatter or damn the result. **(b)'s 80% is a judgement and is labelled one** — a p95 bar
means a *worthless* signal clears 5% of the time, so 80% is sixteen times the null rate while
leaving room for genuine sampling noise on a half-sized book.

**Ambiguous against any bar is a NULL** (`RUN_RULES` A6). **An arm whose half-books are
significantly NEGATIVE in both halves is reported as `REVERSED`, its own verdict**, never folded
into "null".

### 2.4 Kill conditions

* **A failed arm is dead.** No re-cut at a different split fraction, a different `n_q`, a
  market-cap-stratified split, or a subset of dates.
* **If A1 fails, the headline's name-generalisation is REFUTED and that must be reported as the
  session's leading finding**, not as one null among several — it would mean the single most
  quoted number in the project is a property of particular names.

---

## 3. Controls

| id | control | gating? |
|---|---|---|
| **C1** | The **FULL**-universe headline reproduces from this panel before any split: `top_decile_alpha` 0.07174142332098163, LS naive 2.8360640685320595, HAC 2.6199121240414884, monotonicity −0.8909090909090909. **Own pass, aborts before any split.** | **YES** |
| **C2** | Every split is **exhaustive and disjoint**: A ∪ B is the universe, A ∩ B is empty, sizes differ by ≤ 1 — asserted per split, not spot-checked. | **YES** |
| **C3** | The stable key is **deterministic**: recomputing the hash partition yields the identical membership, and it does **not** depend on row order, a seed, or the panel's sort. | no |
| **C4** | **Coverage first**: names per half, rows per half, dates per half, and the realised decile size — so a half-book that is too thin to sort is VOID rather than scored. | no |
| **C5** | The bar used is the **half-universe** null, and X7's full-universe floors are reported **beside** it explicitly labelled as extrapolations. A test pins that the verdict does not read them. | no |
| **C6** | The two halves share **zero** `(date, ticker)` keys — the independence the whole design rests on, asserted rather than assumed. | no |
| **C7** | **R4's BH is applied to already-charged tests only** and charges no equity trial — asserted by listing the signals it covers against `NUMBERS_ALL`. | no |

**Every null draw is banked** (`RUN_RULES` A9).

---

## 4. Expectations, with odds, written before any result

1. **A1 SURVIVES** — the top-decile alpha reproduces on disjoint name halves. 65/35. It is a
   broad-cross-section effect measured on 253-name deciles; halving should widen the error bars
   without moving the centre.
2. **A2 (long-short) does NOT survive**, or survives more marginally than A1. 60/40. The long-short
   leg is already the weaker statistic (HAC 2.62 against alpha's 4.38) and S22 measured that the
   persistence lives entirely in the long leg.
3. **The stable-key split agrees with the random-split majority.** 80/20 — if it did not, the
   primary would be an unlucky draw and would have to be reported as one.
4. **BH at q = 0.05 leaves fewer than 10 of the 53 equity signals surviving.** 60/40.
5. **`gp_on_capital` survives BH**; it is the project's strongest single number. 75/25.
6. **R4 closes `DONE`, not `SUPERSEDED`** — both closable bullets land. 70/30.
7. **The HLZ-vs-calibrated tension (§0b) is the most-quoted thing to come out of this session.**
   60/40, and I record it because it is a prediction about how the result will be *used*, which
   this project has never written down before.
8. **At least one half-book somewhere returns a NEGATIVE top-decile alpha.** 55/45 — 200 half-books
   is a lot of draws.

---

## 5. Trial cost

**X1: two equity trials** (A1 alpha, A2 long-short). **Equity `N` 218 → 220**, haircut
√(2·ln 218) = 3.2816 → √(2·ln 220) = 3.2844.

**R4: one infra trial. Infra `N` 11 → 12.** Accounting over existing measurements; **BH applied to
already-charged tests is a correction, not a search**, and infra `N` gates no published claim.

`N` was **re-measured from `research_log.detail()` after this session's merge** (equity 218,
options 292, unified 0, infra 11), not quoted from `CLAUDE.md`. The `n` column is written as the
literal `n=<k>` form the parser requires.

`BACKTEST_RESULTS.json` is refreshed from a clean tree at the new denominator, and this run's
refresh additionally ships R4's two new blocks.

---

## 6. Void conditions

1. Any `.py` in this file's commit, or this file not being a strict ancestor of every measurement
   commit.
2. Any split family, split fraction, `n_q` or horizon beyond those named in §2.
3. Substituting X7's full-universe floors for the half-universe null.
4. Pointing the permutation at an already-computed composite column rather than recomputing it from
   shuffled themes.
5. A failing **C1** or **C2** with any split result nevertheless read or reported.
6. Charging R4's BH to the equity denominator.
7. Editing this register after any result exists.

---

## 7. What this register does NOT do

* **It does not re-run every theme decision under the universe split.** X1's method paragraph asks
  for that; this register measures **the headline only**, which is the axis the task named and the
  one that carries every published claim. **Re-running the theme decisions is a separate item and
  is named here so it is not mistaken for done.**
* **It does not add a p-value column to the research log** (§1.2) — that would be invention.
* **It does not decide the `unified`-domain question** (§0c) — measured and routed.
* **It does not change any score, weight or threshold.** Nothing under `valuation/` changes except
  the two additive R4 reporting blocks, and the composite is gated bit-identical by C1.
