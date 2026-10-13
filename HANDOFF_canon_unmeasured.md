# HANDOFF — `CANON-UNMEASURED`: the figures the canonical move left UNMEASURED

**Lane:** r1 · **Date:** 2026-10-13 · **Prompt:** `PROMPT_r1_2026-10-13_unmeasured.md`
**Register:** `PREREG_canonmove_unmeasured.md`, committed **ALONE at `e4b0dae`** — one `.md`,
304 lines, zero `.py`, a strict git ancestor of every measurement commit.

**ZERO TRIALS on every item.** Each is a RE-MEASUREMENT of an already-registered construction on
a different universe — the `S25` / `X7RECON` / `MB3` / `CORRECTED-FLOORS` class — so `by_domain`
is bit-identical across the log append (equity **297**, options **315**, infra **20**) and
`rows_fixed_not_counted` rises by one. **ADOPTS NOTHING. NO PUBLIC PAGE CHANGED BY THIS LANE**
(the prompt forbids it); every public figure that moves is handed to the app fixer in §8.

**EVERY FIGURE IS THE DEPLOYED EQUAL-WEIGHT BOOK (flat 1/7)** per `DECISIONS.md` 2026-10-07, and
every row says so. On this universe that label is load-bearing rather than decorative: CPCV
**ADOPTS** `ic-proportional` here, and the adopted book's top-decile alpha is 2.83% against the
deployed 6.07%.

---

## 0. THE CONTROL THAT LICENSES EVERY FIGURE BELOW, AND THE CAVEAT EVERY FIGURE INHERITS

**§0's weighting control passes at |dev| 0.000e+00 on 3 of 3 cells, GATED ON THE COUNT.** The
deployed reading reproduces `CORRECTED_DEPLOYED.json`'s own landed figures exactly — top-decile
alpha `0.060674434603777944`, long-short HAC *t* `4.594456679049444`, monotonicity
`-0.9636363636363636` — so every item is measured against the object the record describes.
The cell count is gated because `MB21`'s `C1` once scored a perfect zero on an empty frame by
comparing nothing.

**THE CAVEAT: the published and corrected panels share ZERO rebalance dates** (2,531 × 69 at
2009-01-15…2026-01-28 against 9,645 × 69 at 2009-03-27…2026-04-09). `X2` measured the grid ALONE
moving the long-short *t* by 0.81. **No old → new move below is attributed to the universe
alone**, and none is so attributed.

---

## 1. THE DEPLOYED BOOK'S DEFLATED SHARPE IS 0.7208, NOT 0.0016 — AND PBO IS NOT A STATISTIC
## ABOUT THAT BOOK IN EITHER DIRECTION

### 1.1 The Deflated Sharpe: **SURVIVES**

| | published | corrected |
|---|---|---|
| Deflated Sharpe, **DEPLOYED** book | **0.786321** | **0.720824** |
| equity `N` (an INPUT to the statistic) | 224 | **297** |
| conventional bar > 0.95 | FAILS | **FAILS** |
| matched non-adopting placebo floor | 0.663664 | **0.565519** (84 draws) |
| clears the calibrated floor | yes | **yes** |

**The claim's relationship to both bars is unchanged, so the state is `SURVIVES`.** And the
comparison is **like-for-like on the BOOK**, checked rather than assumed: the published run's own
`cpcv.adopt` was **False** with `recommend = current-default`, so 0.7863 **is** the deployed
book.

**IT IS 490× THE ADOPTED BOOK'S 0.001472.** Filling the deployed cell from the `cpcv` block —
exactly what `CANONICAL_MOVE_TABLE.md` §0 point 2 warned against — would have published a
near-zero probability for a book that reads 0.72.

### 1.2 MOST OF THE FALL IS THIS PROJECT'S OWN TRIAL COUNTER, NOT THE UNIVERSE

`sr0` is a function of `_trial_N()`, which reads `RESEARCH_LOG.md` at run time, so the two
readings are **not comparable across denominators** (`MA19`'s own recurring defect). Separated
from banked numbers alone, by inverting the banked probability to recover the non-normality
correction — no re-run, no skew/kurtosis needed:

* the **published** book at the corrected `N` = 297 → **0.746246**
* the **corrected** book at the published `N` = 224 → **0.763053**

So of the **0.0655** total fall, roughly **0.040 is `N` rising 224 → 297** — other lanes booking
trials, nothing to do with the universe — and only **0.023–0.025** is the universe and grid.
The deployed book's own raw Sharpe actually **ROSE** (0.5500 → 0.5842); the deflation benchmark
rose faster (0.4605 → 0.5128).

### 1.3 PBO: a precision correction to the move table, declared BEFORE the run

`CANONICAL_MOVE_TABLE.md` §0 point 2 says `cpcv.pbo` *"describes the ADOPTED book"*. **That is
right about the Deflated Sharpe and imprecise about PBO.** `_pbo` never reads `adopt` or
`recommend`: it takes the in-sample argmax per CPCV path and asks whether its out-of-sample rank
sits at or below the median. **So the shipped figure is the SAME number whether or not adoption
happened** — it scores the **selection step** over the eight candidates, which `pbo_scope =
"weight_scheme_selection_only"` already says. **The deployed book selects nothing, so
Bailey–López de Prado's PBO is not a statistic about it in either direction.**

The deployed-book analogue was measured anyway, labelled a NEW statistic: `_pbo` with the argmax
replaced by the fixed `current-default` scheme reads **1.0**, median out-of-sample rank **0.25 of
eight** (13 of 15 paths at 0.25, two at 0.375).

**AND IT MAY NEVER BE PUBLISHED AS A 100% PROBABILITY OF OVERFITTING.** The per-scheme control
proves it is a pure **RANK** statistic, monotone in median out-of-sample IC:

| scheme | fixed PBO | median OOS IC |
|---|---|---|
| ic-proportional | 0.0 | +0.09621 |
| ic-ir | 0.0 | +0.09112 |
| positive-equal | 0.0 | +0.09082 |
| ic-shrunk-50 | 0.333 | +0.08894 |
| equal-weight | 1.0 | +0.07210 |
| max-ir-decorr | 0.667 | +0.07163 |
| **current-default (DEPLOYED)** | **1.0** | **+0.05702** |
| risk-parity | 1.0 | +0.05257 |

For a book chosen by SELECTION, a high value is evidence of selection optimism. For a book that
selects nothing it says only *"there are better-ranking alternatives out of sample"* — which is a
rank fact and carries no overfitting claim. **So the move table's `UNMEASURED` label is the
correct one, and it now has a measured reason rather than an absence.** It has no calibrated
floor either: the retained draws carry `pbo` under the argmax rule only, so it is labelled
**UNCALIBRATED** (`V2G` / `R1-VAR`'s rule) and `X7`'s measurement that pure noise sits at a
**median PBO of 46.7%** travels with every PBO figure here.

### 1.4 The panel edit is PROVED INERT, not asserted

`_pbo` gained an optional `fixed=` (default `None`) and `cpcv_validate` a
`deployed_readings=False` that **adds no key when off**, so `payload_schema.BLOCK_SPEC`'s
field-level guard on the `cpcv` block sees exactly what it saw before (`M6`: a computed field
that reaches the source and not the projection FAILS the run, so a new key must be opt-in or
registered, never silently added).

Differential: `HEAD`'s source restored, probed in a subprocess, the edited source restored
**byte-for-byte** (checked, and refused otherwise — `W-1`'s harness could not put a file back),
**59 leaves before and 59 after, zero moved, zero keys added or removed**, top-level keys
identical. Gated on the leaf count so a zero-difference over zero leaves cannot pass.

**A DEFECT IN MY OWN REPORTING, caught by disbelieving a number.** The raw byte counts are
310,463 and 320,543 — a 10,080 difference that reads as a 10 KB edit, and 10,080 is almost
exactly the CRLF count, because `git show` emits LF while the working copy is CRLF. Both sizes
now ship **normalised** (the edit is **+4,605 bytes / +73 lines**) with the raw pair beside them
and the encoding named. Comparing two sizes in two encodings is the wrong-object family.

---

## 2. `X1` — BOTH ARMS SURVIVE, AND THE LONG-SHORT ARM IMPROVES SHARPLY

Construction and bars **IMPORTED** from `PREREG_r4_x1_accounting_and_universe_split.md`, nothing
retyped: `THEMES`, `W` = 0.125, `K_SPLITS` = 100, `J_NULL` = 200, `SEED` = 20260813,
`MIN_NAMES_PER_HALF` = 400, `FRAC_HALFBOOKS` = 0.80, `FRAC_BOTH` = 0.64, `stable_key_half`,
`_score`, `half_universe_null` and the verdict rule `verdict_of` itself.

**THE WEIGHTING IS THE DEPLOYED BOOK AND THAT IS VERIFIED, NOT ARGUED.** X1's `W` = 0.125 over
seven themes sums to 0.875, and `composite_from_frame` renormalises by the present-weight mass,
so a uniform scaling of every weight cannot move a ranking. Measured: X1's construction
reproduces the corrected DEPLOYED literals at **|dev| 0.000e+00** on all three cells.

**The half-universe null, rebuilt for a HALF book at 200 draws** — and it is well centred, which
is what says the instrument is sound: alpha median **+0.000863**, long-short HAC *t* median
**−0.0594**, both about zero.

| | A1 top-decile alpha | A2 long-short HAC *t* |
|---|---|---|
| half-universe null p95 (the bar) | **+0.013414** | **+1.4661** |
| stable-key half A / half B | +0.054666 / +0.059699 | +4.3251 / +4.4646 |
| primary — both halves clear AND positive | **TRUE** | **TRUE** |
| half books clearing p95 (bar 0.80) | **1.000** (200 of 200) | **1.000** (200 of 200) |
| splits clearing on BOTH sides (bar 0.64) | **1.000** (100 of 100) | **1.000** (100 of 100) |
| splits NEGATIVE on both sides (REVERSED at 0.64) | 0.000 | 0.000 |
| half-book median / min / max | +0.06046 / **+0.04189** / +0.07679 | +4.3727 / **+3.2940** / +5.7055 |
| half books negative | **0 of 200** | **0 of 200** |
| full universe, corrected | +0.060674 | +4.594457 |
| **verdict** | **SURVIVES** | **SURVIVES** |

**THE SENTENCE THE MOVE TABLE FORBADE RESTATING NOW RESTATES VERBATIM.** *"400 half-universe
books, not one negative"* — 200 half books per arm × two arms = 400 measurements, **zero
negative**, exactly as on the published universe. **The worst of 200 half books still earns
+4.19%/yr and the worst long-short *t* is still 3.29.**

**AND A2 IS THE ARM THAT MOVED.** On the published universe A1 cleared 200 of 200 half books and
A2 only **93.0%**, with 14 of 200 failing and 86.0% of splits clearing both sides — A1 was the
stronger claim and had to be quoted as such. On the corrected universe **both are 100%/100%** and
A2's median half-book *t* rises **+2.3617 → +4.3727**. The asymmetry the published record carried
is gone. A1's level is slightly lower (median +0.07233 → +0.06046), which is the universe's own
alpha falling rather than the split degrading.

**CONTROLS.** `C3` the stable key is deterministic and order-independent; `C6` the halves share
**zero** `(date, ticker)` keys; `C4` half books hold a median **4,822 names / 144,980 rows**, an
implied decile of **210 names** against the full universe's 420; `C5` X7's full-universe floors
are reported BESIDE the half-universe null and never AS it — on this universe they are an
extrapolation **twice** over (different universe, half book).

**`MIN_NAMES_PER_HALF` = 400 IS INHERITED AND DOES NOT BIND** (each half is ~4,822 names).
Reported rather than removed.

**WHAT A PASS DOES NOT LICENSE, fixed before the outcome:** X1 tests generalisation across
NAMES, not decision leakage — the deployed strategy fits nothing, so there is no decision to
leak. Re-running every theme decision and the weight selection under the split is **NOT done**.

---

## 3. `R1`'s NET-OF-COST CELL CLEARS ITS OWN BAR — AND FAILS IF BOTH TRADE LEGS ARE CHARGED

### 3.1 The diagnosis, measured

`factor_alpha`'s `net_of_cost` LEFT-joins `X4`'s shipped
`ETF_BENCHMARK_RESULTS_strategy_series.csv` for `turnover` and `cost_bps`. That CSV is indexed on
X4's own **110-date** grid; the overlap with the corrected grid is **0 of 69**, so `cost` is
all-NaN and every net cell is NaN. The `E-6` family — a merge keyed on another object's dates —
except that it produced NaN rather than silence, so it was visible.

**AND THE CELL HAS BEEN UNMEASURABLE SINCE `B6`, NOT SINCE THIS MOVE.** Pre-committed to be
checked and reported either way: the **PUBLISHED** 2,531 × 69 panel shares **0 dates** with that
CSV too. So R1's own net leg could not have been measured on the published panel either, and the
shipped **+7.85%/yr (t 5.16)** is `FACTOR_ALPHA_RESULTS.json`'s **109-period VOID pre-B6 run**,
which `CLAUDE.md` already labels void.

### 3.2 The fix is an INPUT, not an edit to R1

`--strategy-series` is an argument; the corrected series is built by the shipped producer
`etf_benchmark.strategy_series`, **called**. `cost = (cost_bps / 1e4) × turnover` stays exactly
as R1 wrote it, and **the gross leg is the control**: it reproduces the landed
`+0.059397599064971024` at *t* `+4.453158903833538` at **dev 0.000e+00** on all three readings,
so it is the same regression.

| reading | cost drag /yr | net intercept /yr | NW *t* | R1's bar (positive, *t* > 2.0) |
|---|---|---|---|---|
| **PRIMARY** — shipped composite | 1.8787% | **+4.0583%** | **+3.0094** | **CLEARS** |
| SENSITIVITY — pre-B7 legacy composite | 1.8298% | +4.1099% | +3.0420 | clears |
| **SENSITIVITY — BOTH trade legs charged** | 3.6903% | **+2.2936%** | **+1.7084** | **DOES NOT CLEAR** |

### 3.3 Two things that must travel with those numbers

**THE COMPOSITE CHOICE IS IMMATERIAL AND WAS CHECKED RATHER THAN ASSUMED.**
`strategy_series` built its book from the **pre-`B7` non-renormalising** composite while
`factor_alpha.decile_series` calls the **shipped** one, so the COST described a different book
from the RETURN it was charged against. It gains `legacy_composite=True` **defaulting to the
landed convention** — `decile_series`'s own precedent, for the same reason and in the same words
— and the default is proved **bit-identical to HEAD's loop** on 69 of 69 periods across all five
columns. The two readings differ by 0.05pp.

**REPORTED, NOT FIXED (`RUN_RULES` rule 3), AND IT IS DECISION-RELEVANT.**
`cost = (cost_bps/1e4) × turnover` charges the one-way cost on the **ENTERING** side only
(`turnover` is `len(entering)/k`), while `fundamental_panel.turnover_and_costs` charges
`(bps/1e4) × (n_bought + n_sold)/len(held)` — **two-way**. R1's leg therefore undercharges by
about a factor of two against this project's own cost model. **R1's registered formula is run as
written and it clears; charging both legs it does not.** Both ship. Re-pointing R1's formula is a
different register's business, and a successor that wants to should note that `/methodology`
currently carries no net-of-cost figure at all.

---

## 4.1 `P1S0` — THE OPTIONABLE NUMERATOR BARELY MOVES, SO "ROUGHLY A QUARTER" IS WRONG BY 3.7×

| | published | corrected |
|---|---|---|
| `N_PANEL_NAMES` | 2,531 | **9,645** |
| `N_OPTIONABLE_NAMES` (`pit_liquid`, PRIMARY) | 619 | **630** |
| names with ANY point-in-time chain | — | **923** |
| **optionable share of the panel** | **24.46%** | **6.53%** |
| dates with any chain | 40 of 69 | **39 of 69** |
| first / last covered | 2016-01-20 / 2025-10-27 | **2016-03-31 / 2025-10-07** |
| median `pit_liquid` names per covered date | 287.5 | **280.0** |

**THE NUMERATOR IS ESSENTIALLY A CONSTANT: 619 → 630, up 1.8%, while the denominator went 3.8×.**
The chain cache is a **targeted pull** of large, liquid names — 1,000 ticker directories on disk,
923 of them in the corrected panel — so widening the universe cannot widen it. That is the whole
of the share's fall, and it was the register's own expectation 8 (85/15, **right**).

**THE PUBLIC COPY IS THE THING THAT CHANGES.** `valuation/web/optionable_partition.py`'s lede
says *"Roughly a quarter of the research panel has listed options"* and `WHAT_IT_IS` formats the
two stamps into a sentence. **At 6.53% "roughly a quarter" is wrong by 3.7×** — it is closer to
*one name in fifteen*. The move table's instruction is honoured: the stamp moves **only with its
figures**, and both move together.

**P1S0's OWN VERDICT IS CARRIED, NOT RE-DECIDED** — and there is one observation that must be
reported and must not be scored.

| h | alpha_ann full | early | late | full panel, same dates |
|---|---|---|---|---|
| 63 (`pit_liquid`, the power anchor) | +15.46% (*t* 3.06) | **+7.40% (*t* 1.82)** | +16.42% (*t* 3.10) | +8.14% |
| 252 | +17.41% (*t* 2.82) | **+14.81% (*t* 1.49)** | +19.63% (*t* 2.65) | +3.74% |
| 504 | +8.06% (*t* 2.44) | **+5.28% (*t* 2.03)** | +10.84% (*t* 1.86) | +2.85% |

**`P1S0` CLOSED THE OPTIONS-EXPRESSION FAMILY ON AN EARLY HALF THAT WAS ABSENT — AND ON THE
CORRECTED PANEL IT IS NOT ABSENT.** Its own early-half readings were a cumulative alpha of
**−0.08%** at H=252 and *t* **0.8352** at the H=63 power anchor. Here every early-half cell is
**positive** at every horizon and in both partition modes, and the optionable subset beats the
full panel over the same dates at all three horizons.

**THAT IS REPORTED AND CARRIES NO VERDICT, for three reasons fixed in the register before the
run.** (a) **The per-horizon placebo floors were NOT re-run on this universe**, so no cell here
is scored against a calibrated bar, and comparing to the published floors would be the
extrapolation `P1S0` built its own nulls to avoid. (b) The window is **39 post-2016 dates**, not
the 69 the headline is measured on, so these alphas are not comparable with the 6.07%.
(c) Re-opening the family is **Don's**, needs its own blind register and its own floors, and is
**not proposed here**. `P1S0-CONTROL`'s NULL is not re-opened either.

**ROUTED TO DON:** the one fact worth his attention is that the family's closure rested on an
early-half absence that does not reproduce on the corrected universe.

---

## 4.2 `V6-B` M1 — `REAL`, AND LARGER THAN ON THE PUBLISHED PANEL

**C1's gate is re-pointed and it was the thing that had blocked this.** The earlier corrected
attempt aborted at `[C1] reproduces the record: False` against the PUBLISHED literals, on a panel
its own `C2` had just certified as canonical — a guard firing on the clock rather than on the
property it protects. `--expect-record` makes the literals re-pointable, **defaults to `REC`
verbatim** so every existing invocation is bit-identical, and the corrected expectation is
**DERIVED** from a fresh `quantile_backtest` rather than typed. It reproduces at **dev 0.000e+00**
on all three of the move's own deployed cells. Bars IMPORTED from `PREREG_v6b_dip_survival.md`
and never restated (its void condition 6.3).

**M1 verdict: `REAL — HEALTHY DIPS SURVIVE BETTER`.**

| registered per-date statistic | published | corrected |
|---|---|---|
| full sample | −10.228pp at *t* −10.585 | **−12.153pp at *t* −12.777** |
| early half | −9.064pp | **−10.311pp at *t* −8.386** |
| late half | −11.515pp | **−13.867pp at *t* −10.379** |
| halves same sign / both below own p5 | yes / yes | **yes / yes** |
| own-permutation p5 (full, 500 draws) | −1.707 | **−1.718** |
| pre-committed economic floor | 3.0pp | 3.0pp — **cleared 4.05×** |
| MDE at \|*t*\| = 2 | 1.933pp | **1.902pp — the effect is 6.4× its own detection threshold** |

Population: **117,113** dipped rows with a full 126-day forward window (29,565 healthy /
87,548 unhealthy) over 68 dates; 3,756 censored rows dropped rather than scored on a short
window. `C3` **zero** point-in-time violations; `C5` **zero** rows flagged both distress and
acquisition.

**THE CAVEAT TRAVELS, AND IT IS THE SAME ONE:** `C8` measures the healthy dipped set at **1.98×**
the median market cap of the unhealthy one (published 2.06×), so a size sort must not be
reportable as a health finding. **The within-quintile stratification that bounds it is in
`CANON_UNMEASURED_V6B_ADDENDUM.json`** — the `v6b_addendum` producer had its paths hard-coded and
is now parameterised, which is the third instance of that defect family this lane found.

**AND `M2` BECOMES ANSWERABLE FOR THE FIRST TIME, AND THE ANSWER IS `NULL`.** The published run
recorded M2 (distress within 252 days) **VOID — UNDERPOWERED BY CONSTRUCTION** at **42** distress
events against its own floor of 60, so its numbers were never read. The corrected universe
supplies **170**, so the arm runs — and it fails the both-halves rule: full **−0.1181pp** at
*t* −4.753 clears its own p5, the **late** half clears at *t* −5.737, and the **early** half does
not (−0.0317pp at *t* −1.439 against a p5 of −2.336). **So the distress metric is NULL rather
than void, which is a stronger statement than the published record could make.** M3 stays
`DESCRIPTIVE — NO VERDICT BY REGISTER 2.1`.

**NOT DONE:** the dip branch is not re-opened, no floor is re-tuned (void condition 6.3), and
`V6`'s own four nulls are untouched.

---

## 4.4 THE LIVE / FORWARD TRACK RECORD — `UNMEASURED-BY-CONSTRUCTION`

Pre-committed in the register §4.4 before anything ran, and it is a **different state** from
every other row here: the others could be measured and were; this one cannot be measured by
anyone today. It is a forward record accruing in calendar time under
`PAPER_TRACK_CONTRACT.md`; no backtest on any universe produces it, backfilling it is forbidden
by a standing security rule, and the contract's frozen meter parameters are outside this lane.
**What would change it is elapsed calendar time and nothing else.** The recorded series was READ
only, to say how long it is (10 rows, last 2026-10-08, day 49); no figure from it is quoted as a
verdict and nothing was written.

---

## 8. FOR THE APP FIXER — public figures that move

**No page is changed by this lane.** These are handed over:

| surface | symbol / figure | published | corrected |
|---|---|---|---|
| `/proof` (LIVE read of `BACKTEST_RESULTS.json`) | Deflated Sharpe bar, DEPLOYED book | 0.7863 — FAILS >0.95 | **0.7208 — still FAILS >0.95, CLEARS the calibrated 0.5655** |
| `/proof` | PBO bar | 0.7333 — FAILS | **stays UNMEASURED, with a measured reason (§1.3)** |
| `/methodology` (TEMPLATE) | R1's net-of-cost specification | UNMEASURED | **+4.06%/yr, NW *t* 3.01** (and +2.29%/yr at *t* 1.71 charging both legs) |
| `valuation/web/optionable_partition.py` | `N_PANEL_NAMES` | 2531 | **9645** |
| " | `N_OPTIONABLE_NAMES` | 619 | **630** |
| " | the lede's *"roughly a quarter of the research panel has listed options"* | 24.46% | **6.53% — the copy is WRONG by 3.7× and is the real change; "one name in fifteen" is the honest phrasing** |
| README / START_HERE (LITERALS) | *"400 half-universe books, not one negative"* | UNMEASURED | **RESTATES VERBATIM** — 400 measurements on the corrected universe, zero negative, both arms 100%/100% |

**THE `/proof` CELLS NEED A CANONICAL RE-RUN BEFORE THEY CAN BE READ LIVE.** `/proof` reads
`cpcv.pbo` and `cpcv.deflated_sharpe` out of the tracked artifact, and those are the **ADOPTED**
book's. The deployed readings exist in `data/free_analysis/CANON_UNMEASURED_DEPLOYED.json` and
reach the tracked artifact only on a run with `cpcv_validate(deployed_readings=True)` — which
means registering the two new fields in `payload_schema.BLOCK_SPEC` so `M6`'s guard carries them
rather than failing the run. **That is a canonical re-run plus an artifact swap and is explicitly
out of this lane's scope** (`CANONICAL_MOVE_TABLE.md` §7). Until it happens, the honest surface is
the move table's own: show the Deflated Sharpe from the research record with its `N`, and PBO as
UNMEASURED with §1.3's reason.

**AND `N` MUST TRAVEL WITH THE DEFLATED SHARPE WHEREVER IT IS SHOWN.** It moves at every trial
any lane books; §1.2 measures that as the larger half of the figure's own change.

---

## BUGS FOUND

1. **`scripts/canon_figure_table.py` had THREE dead hard-coded paths, and the failure mode was
   SILENT ROW LOSS.** `WT` pointed at `.claude/worktrees/r1b` (which no longer holds a
   `BACKTEST_RESULTS.json`) and `TMP` at a job scratch directory since cleaned up. `load()`
   returns `None` for an absent file and the `BACKTEST_RESULTS.json` block is guarded by
   `if canon and before`, so **regenerating `CANONICAL_FIGURE_TABLE.md` today would have dropped
   15 rows — including every public landing-page figure — and printed a cheerful row count.**
   **FIXED:** every path derived; the "published" column read from **git** at
   `ARTIFACT_SWAP_COMMIT^` so it is reproducible by anyone holding the repo and cannot rot; and
   both loads now **REFUSE** rather than returning `None`. *A generated file whose generator
   silently shrinks is worse than a hand-edited one, because nothing says the table got smaller.*
2. **`X1`'s own `C2` control asserted a property its PRIMARY split does not have, and it passed
   on the published universe by a ~1-in-32 fluke.** `_assert_split` required
   `|len(A) − len(B)| ≤ 1` for BOTH the random splits (balanced **by construction**, where 1 is
   right) and the `sha1(ticker) % 2` split (balanced only **in expectation**, imbalance sd
   `sqrt(n)`). On 2,531 names it read 1266/1265 and `P(|imbalance| == 1)` under a fair hash is
   **0.0317**; on 9,645 it reads 4798/4847 — imbalance **49 against an sd of 98.2, z = 0.50** —
   and **it fired on a split that is exactly what the construction promises.**
   **FIXED:** `balance_tol` is a parameter defaulting to **1** (every existing caller unaffected),
   and the hash split is passed a **DERIVED** 4-sigma tolerance `2*sqrt(n) = 196`, never a chosen
   one. *This is not a relaxed check; it is the check pointed at the property `C2` stood in for.*
3. **`V6-B`'s `C1` gate aborted the corrected run against the PUBLISHED literals**, on a panel
   its own `C2` had just certified as canonical (`CORRECTED_V6B.log`:
   `[C1] reproduces the record: False`). The same clock-shaped guard as bug 2.
   **FIXED:** `--expect-record` makes the literals re-pointable, defaulting to `REC` verbatim so
   every existing invocation is bit-identical. `C1`'s RULE is kept; only its literals move, and
   the corrected literals are **DERIVED** from a fresh `quantile_backtest` rather than typed.
4. **`scripts/factor_alpha.py`'s `net_of_cost` block left-joins a series on another panel's
   grid** — §3.1. **REPORTED, NOT FIXED** inside R1's instrument: its cost formula is R1's and
   re-pointing it would move a landed figure. The lane supplied a corrected input instead.
5. **`factor_alpha`'s cost formula charges one trade leg, not two** — §3.3. **REPORTED, NOT
   FIXED**, with the two-way sensitivity beside it because the discrepancy crosses R1's bar.
6. **`CANONICAL_MOVE_TABLE.md` §0 point 2's description of `cpcv.pbo` is imprecise** — §1.3.
   Corrected in this lane's own successor rows rather than by editing the hand-off table's
   historical text.
