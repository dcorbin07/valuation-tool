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

## 8. FOR THE APP FIXER — public figures that move

**No page is changed by this lane.** These are handed over:

| surface | symbol / figure | published | corrected |
|---|---|---|---|
| `/proof` (LIVE read of `BACKTEST_RESULTS.json`) | Deflated Sharpe bar, DEPLOYED book | 0.7863 — FAILS >0.95 | **0.7208 — still FAILS >0.95, CLEARS the calibrated 0.5655** |
| `/proof` | PBO bar | 0.7333 — FAILS | **stays UNMEASURED, with a measured reason (§1.3)** |
| `/methodology` (TEMPLATE) | R1's net-of-cost specification | UNMEASURED | **+4.06%/yr, NW *t* 3.01** (and +2.29%/yr at *t* 1.71 charging both legs) |

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
