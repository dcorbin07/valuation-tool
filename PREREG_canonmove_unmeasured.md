# PREREG — `CANON-UNMEASURED` — the figures the canonical move left UNMEASURED

**Committed ALONE, before any measurement code for these items exists in this worktree.**
Markdown only, zero `.py`. A strict git ancestor of every commit that computes a number below.

**ZERO TRIALS. Every item here is a RE-MEASUREMENT of an ALREADY-REGISTERED construction** on a
different universe — the `S25` / `X7RECON` / `MB3` / `CORRECTED-FLOORS` class. No hypothesis is
formed here, no bar is chosen here, and no arm is added to any register. **Every threshold below
is INHERITED VERBATIM from the register that first set it**, and where a bar cannot be inherited
that is stated as a limitation rather than repaired by choosing a new one (`W-28` §6: a successor
may not relax a pre-committed bar after watching it fail, and the mirror holds — it may not
invent one after watching a floor go missing).

**ADOPTS NOTHING. CHANGES NO PUBLIC PAGE** (the prompt forbids a page change by this lane).
Any public figure that moves is HANDED to the app-fixer lane, not shipped.

---

## 0. THE CAVEAT EVERY ITEM INHERITS, AND IT IS `CANONICAL_MOVE_TABLE.md` §0

**The published and corrected panels share ZERO rebalance dates** (2,531 × 69 dates
2009-01-15…2026-01-28 against 9,645 × 69 dates 2009-03-27…2026-04-09). The grid derives from the
universe's own trading calendar, and `X2` measured the grid ALONE moving the long-short *t* by
0.81. **So no old → new move recorded below is attributable to the universe alone**, and none is
so attributed.

**EVERY FIGURE IS THE DEPLOYED EQUAL-WEIGHT BOOK (flat 1/7)**, per `DECISIONS.md` 2026-10-07, and
every row says so. That label is load-bearing on this universe rather than decorative: CPCV
**ADOPTS** `ic-proportional` here and the adopted book's top-decile alpha is 2.83% against the
deployed 6.07%.

**THE WEIGHTING CONTROL, PRE-COMMITTED: the deployed reading must reproduce `CORRECTED_DEPLOYED`'s
own landed figures** — top-decile alpha `0.060674434603777944`, long-short HAC *t*
`4.594456679049444`, monotonicity `-0.9636363636363636` — **at |dev| 0.000e+00, or every item
below is VOID.** A re-measurement that cannot reproduce the object it is re-measuring is measuring
something else (`MB21`'s `C1`, and `MA28`'s C1 which fired on its own first run).

**AND THE CONTROL MUST BE NON-VACUOUS.** The count of compared cells is gated and reported:
`MB21`'s `C1` once scored a perfect 0.000e+00 on an empty frame by comparing nothing.

---

## 1. THE DEPLOYED BOOK'S PBO AND DEFLATED SHARPE

### 1.1 What is actually unmeasured, stated precisely before anything is run

`CANONICAL_MOVE_TABLE.md` §0 point 2 records that `cpcv.pbo` and `cpcv.deflated_sharpe`
*"describe the ADOPTED book"*. **That is right about the Deflated Sharpe and it is IMPRECISE about
PBO, and the distinction is declared here BEFORE the measurement rather than discovered after it.**

* `_deflated_sharpe_detail` is fed `_strategy_returns(panel, cols, all_w[recname])`, and `recname`
  is the ADOPTED scheme. **So the DSR genuinely describes a different book** and a deployed
  reading is a different number.
* `_pbo(is_mat, oos_mat, names)` takes the IS-argmax per CPCV path and asks whether its OOS rank
  sits at or below the OOS median. **It never reads `adopt` or `recname`**, so the shipped PBO is
  the SAME number whether or not adoption happened. It is a property of the **selection step over
  the eight candidates**, which is what `pbo_scope = "weight_scheme_selection_only"` already says.
  **The deployed book makes no selection, so Bailey–López de Prado's PBO is not a statistic about
  it at all** — it is neither "the adopted book's PBO" nor an unmeasured property of the deployed
  one.

### 1.2 The two objects measured, both named in advance

* **`DSR_DEPLOYED`** — `_deflated_sharpe_detail(_strategy_returns(panel, cols, base), trial_sr)`,
  the SHIPPED function CALLED (`B7`), with `base` = flat 1/7 and `trial_sr` the same eight-scheme
  Sharpe vector `cpcv_validate` already builds. The only thing that differs from the landed
  reading is **which scheme's return series is in the numerator.**
* **`PBO_NO_SELECTION`** — the same rank arithmetic as `_pbo`, with the IS-argmax replaced by the
  FIXED `current-default` scheme: across the CPCV paths, how often does the book this project
  actually runs land at or below the OOS median of the eight candidates? **This is the honest
  deployed-book analogue and it is a NEW STATISTIC, so it is labelled one.** It is implemented by
  giving `_pbo` an optional `fixed=` argument — ONE implementation of the rank arithmetic, two
  selection rules — and the default path must stay **bit-identical**, proved by measurement and by
  mutation, not asserted.

### 1.3 The bars, INHERITED

| statistic | conventional bar | calibrated floor | inherited from |
|---|---|---|---|
| Deflated Sharpe | **> 0.95** | **p95 of the matched NON-ADOPTING placebo sub-null** | `X7`; `corrected_floors.FLOORS`; `CORRECTED-FLOORS` part 1b's matched-null rule |
| PBO | **< 0.50** | **p05 of the placebo draws** | `X7`; `corrected_floors.FLOORS` (`pbo` is the ONLY low-tail floor) |

**AND ONE OF THOSE FOUR COMPARISONS IS DECLARED UNAVAILABLE IN ADVANCE.** The retained draws
carry `pbo` under the SELECTION rule, so **no floor exists for `PBO_NO_SELECTION` and none is
invented.** It is reported against the conventional 0.50 and labelled **UNCALIBRATED**; deriving
its floor needs the no-selection PBO recomputed on all 100 draws, i.e. a re-sweep, which is named
as not-done. `V2G` / `R1-VAR`'s rule: a critical value with no calibration is labelled, never
quoted bare.

**`X7`'s own measurement of the PBO bar travels with every PBO figure below**: pure noise sits at
a MEDIAN PBO of 46.7%, so "<0.50" has almost no power and is cited as a pass or a fail nowhere.

### 1.4 `N` IS AN INPUT TO THE DEFLATED SHARPE AND IS DERIVED, NEVER QUOTED

`sr0` is a function of `_trial_N()`, which reads `RESEARCH_LOG.md` at run time. The landed
corrected DSR (0.001561) was computed at equity `N` = 285 and **the live `N` has moved since**, so
the deployed reading is reported with the `N` it was taken at, both figures' `N` stated, and the
two are never compared across denominators (`MA19`'s own recurring defect: a numerator at one `N`
paired with a floor at another).

---

## 2. `X1` — THE NAME SPLIT, ON THE CORRECTED UNIVERSE

**The construction is `PREREG_r4_x1_accounting_and_universe_split.md`'s, unmodified**: the
stable-key partition `int(sha1(ticker).hexdigest(), 16) % 2` as the PRIMARY, inside `K_SPLITS` =
100 random splits, against a null **rebuilt for a HALF book** at `J_NULL` = 200 draws, seed
`20260813`, deployed flat 1/7, `horizon` 63, `n_q` 10. Every constant is **IMPORTED from that
script, not retyped** (`MA5`).

**The bars, INHERITED verbatim from its §2.3** and read through its own `verdict_of`, imported so
the rule lives in one place:

* **PRIMARY** — both stable-key halves clear the half-universe null's **p95** AND both are
  positive.
* `FRAC_HALFBOOKS` ≥ **0.80** of the 200 half-books clear p95.
* `FRAC_BOTH` ≥ **0.64** of the 100 splits clear on BOTH sides (derived, 0.80²).
* **REVERSED** if ≥ 0.64 of splits are below p05 on BOTH sides.
* Verdict vocabulary: **SURVIVES / NULL / REVERSED**.
* Arms: `A1_top_decile_alpha`, `A2_long_short_hac_t`. Both reported; neither is dropped.

**ONE CONTROL MUST BE RE-POINTED AND THE RE-POINT IS DECLARED HERE, BEFORE THE RUN.** That script's
`C1` gates on the **PUBLISHED** headline literals (`REC`: alpha 0.07174142332098163, naive *t*
2.8360640685320595, HAC *t* 2.6199121240414884, monotonicity −0.8909090909090909) and aborts
otherwise. **On the corrected panel those cannot reproduce by construction**, so leaving the gate
as written would abort the item for doing exactly what it was asked to do — `W-1`'s `K4` and
`MB31`'s tripwire, both of which fired against correct panels. It is re-pointed to **§0's
corrected deployed literals**, which is the property the gate stood in for: *the split arms are
scored against the same object the record describes.* `C0`'s canonical-panel shape gate is
re-pointed the same way (69 dates, ≥ 9,000 names).

**`MIN_NAMES_PER_HALF` = 400 is inherited and does not bind** (each half is ~4,822 names), and
that is reported rather than removed.

**X7's FULL-universe floors are reported BESIDE the half-universe null and never AS it** — §2.2's
`C5`, and on this universe they are an EXTRAPOLATION twice over (different universe, half book).

**WHAT A PASS DOES AND DOES NOT LICENSE, fixed before the outcome:** `X1` tests generalisation
across NAMES, not decision leakage, because the deployed strategy fits nothing. The sentence
*"400 half-universe books, not one negative"* may be restated **only** with the corrected
universe's own count, or not at all.

---

## 3. `R1`'s NET-OF-COST FACTOR-ALPHA CELL

### 3.1 The diagnosis, recorded before the fix

`scripts/factor_alpha.py`'s `net_of_cost` block left-joins `X4`'s shipped
`ETF_BENCHMARK_RESULTS_strategy_series.csv` for `turnover` and `cost_bps`
(`how="left"`). **That CSV is indexed on X4's own 110-date VOID pre-B6 grid**, which shares
**ZERO dates with the corrected grid**, so `cost` is all-NaN and every net figure is NaN. The
`E-6` family — a merge keyed on another object's dates — except that it produced NaN rather than
silence, so it was visible.

**AND THE CELL HAS BEEN UNMEASURABLE SINCE `B6`, NOT SINCE THIS MOVE.** Pre-committed to be
checked and reported either way: the **PUBLISHED** 2,531 × 69 panel also shares **zero** dates
with that CSV, so R1's own net-of-cost leg could not have been measured on the published panel
either. The shipped `+7.85%/yr (t 5.16)` is `FACTOR_ALPHA_RESULTS.json`'s **109-period VOID run**,
which `CLAUDE.md` already labels void.

### 3.2 What is measured, and what is NOT edited

**R1's arithmetic is NOT changed and `factor_alpha.py`'s cost formula is NOT re-pointed.** The
instrument takes `--strategy-series` as an argument; the fix is to **supply a CORRECTED input on
the corrected grid**, which is what that argument is for. `cost = (cost_bps / 1e4) × turnover`
stays exactly as R1 wrote it.

The corrected series is built by the **shipped producer**, `scripts/etf_benchmark.strategy_series`,
CALLED rather than reimplemented. Its definitions are inherited verbatim: `turnover` = the fraction
of the decile that is NEW this period, `cost_bps` = the mean `one_way_cost_bps(market_cap)` over
the ENTERING names only.

**ONE PARAMETER IS ADDED TO THE PRODUCER AND IT IS DEFAULTED TO THE LANDED BEHAVIOUR.**
`strategy_series` builds its book from the **PRE-`B7` non-renormalising** composite
(`comp + where(isnan(z), 0, z) * w`) while `factor_alpha.decile_series` calls the **shipped**
composite — so as it stands the cost would describe a slightly different book from the return it
is charged against. It gains `legacy_composite=True` **defaulting to the landed convention**, the
exact precedent `decile_series` already set for the same reason. **The primary reading uses the
SHIPPED composite** (`B7`: one composite for selection, measurement and live) and the legacy
reading ships beside it as a **labelled sensitivity**, so the composite choice is bounded rather
than assumed.

### 3.3 The bar, INHERITED

`HANDOFF_r1.md` §1, verbatim and unchanged: **the FF5+MOM intercept is positive with
Newey–West *t* > 2.0**; ambiguous against it is a NULL, never a judgement call. `nw_lag` = 1, as
landed. Both of R1's own net objects are reported — `top_minus_ew` (the registered primary) and
`top_excess_rf`.

**AND THE GROSS LEG IS THE CONTROL:** the corrected gross intercept must reproduce
`CORRECTED_R1_FACTOR_ALPHA.json`'s landed `+0.059397599064971024` at *t* `+4.453158903833538`, or
the net reading is VOID — it would be a different regression.

**REPORTED, NOT FIXED (`RUN_RULES` rule 3).** `cost = (cost_bps/1e4) × turnover` charges the
one-way cost on the **ENTERING** side only, while `turnover_and_costs` charges
`(bps/1e4) × (n_bought + n_sold)/len(held)` — **two-way**. R1's leg therefore undercharges by
about a factor of two relative to the project's own cost model. **It is R1's registered formula
and it is run as written**; the discrepancy is reported with both numbers, and a two-way
sensitivity ships beside the primary so the direction is bounded. Re-pointing it is a different
register's business.

---

## 4. THE REMAINING `UNMEASURED` ROWS, IN THE TWO TABLES' OWN ORDER

Taken in the order the tables list them. Each is a re-measurement of its own register, each
carries that register's bars, and **an item that cannot be measured is recorded as such with its
reason** — never left looking done, and never filled in from a neighbouring figure.

### 4.1 `P1S0` / `valuation/web/optionable_partition.py` `N_PANEL_NAMES`

The stamp reads `2531`. **The move table's own instruction is inherited: move the stamp ONLY with
its figures.** So the measurement is the optionable partition's own coverage and gate on the
corrected panel — how many of the 9,645 names carry a point-in-time chain, on how many of the 69
corrected dates — and the stamp moves only if the partition's figures move with it. Bars inherited
from `PREREG_p1s0_optionable_gate.md`; its own verdict (a both-halves failure that closed the
options-expression family) is **carried, not re-decided**, and `P1S0-CONTROL`'s `NULL` is not
re-opened.

### 4.2 `V6-B` M1 — healthy dips fall a further 20% less often (32.5% vs 43.4%)

`scripts/v6b_dip_survival.py`, bars IMPORTED from `V6`/`V6-B` and never restated (void condition
6.3): the registered per-date statistic, the pre-committed **3.0pp economic floor**, both halves,
`N_PERM` = 500 within-date permutations, `MIN_PER_SIDE` = 10, `MIN_DATES_PER_HALF` = 24.

**ITS `C1` ABORTED THE CORRECTED RUN AND THE RE-POINT IS DECLARED HERE.** `CORRECTED_V6B.log`
reads `[C1] reproduces the record: False` on a panel its own `C2` had just certified as canonical
(69 dates, 9,645 names) — the same clock-shaped gate as `X1`'s `C1`, firing against a correct
panel. Re-pointed to the corrected panel's own figures, as in §2. **The merge-coverage gates
(`drawdown_cov`, `health_cov`, `fwd_min_cov`) are NOT relaxed** — these panels carry STRING dates
and a `Timestamp`-keyed merge matches zero rows in silence, so a collapsed join must still refuse
rather than surface as a null.

### 4.3 `S22`'s eight per-horizon `fixed_weights_null` floors

Eight horizons × 200 draws, the construction `S22` registered. **`MB21`'s standing caveat travels
with any figure read off it: `fixed_weights_null` permutes WITHIN each date, so it has no memory
and is a DIFFERENT, less conservative null than `placebo_panel` with selection in the loop.** Its
percentiles may never be compared with the 2.2837-family floors. If the draw count cannot be met
it is reported **PARTIAL**, never quoted as a floor (`corrected_floors.MIN_DRAWS_FOR_A_FLOOR`'s
rule: a p95 over 20 draws is set by its single largest value).

### 4.4 The live / forward Track Record

**Pre-committed as NOT RE-MEASURABLE, and the reason is structural rather than a shortfall of
effort.** It is a forward record that accrues in calendar time under
`PAPER_TRACK_CONTRACT.md`; a backtest on any universe cannot produce it, backfilling it is
forbidden by a standing security rule, and the contract's frozen meter parameters are not touched
by this lane. It is reported **UNMEASURED-BY-CONSTRUCTION** with that reason attached, which is a
different state from the other rows and is labelled differently.

---

## 5. VOID CONDITIONS

1. **The §0 weighting control must pass at |dev| 0.000e+00 with a non-zero compared-cell count**,
   or every figure here is void.
2. **No bar below may be re-chosen after its figure is read.** Every threshold is inherited and
   cited; a figure whose bar cannot be inherited is labelled UNCALIBRATED and carries no verdict
   against a number chosen here.
3. **No new arm.** Nothing here sweeps a parameter, adds a horizon, adds a split rule, or scores a
   hypothesis the original register did not register. A sensitivity is LABELLED one and carries no
   verdict.
4. **No public page is changed by this lane**, and the tracked `BACKTEST_RESULTS.json` is not
   re-generated or swapped. Public figures that move are HANDED to the app fixer.
5. **`CANONICAL_FIGURE_TABLE.md` is GENERATED and is never hand-edited**; it is regenerated with
   `scripts/canon_figure_table.py`. A figure that reaches it by hand is void.
6. **Quoting the published figure beside the corrected one is required, not forbidden** — but no
   move may be attributed to the universe alone (§0).

---

## 6. WHAT I EXPECT, WRITTEN DOWN BEFORE THE RUN

Scored afterwards, right or wrong. This record's own repeated lesson is that its expectations
about the direction of its own effects have been wrong more often than right.

1. **`DSR_DEPLOYED` will be far ABOVE the adopted book's 0.0016 and still FAR BELOW 0.95** —
   70/30. The deployed book's alpha is more than double the adopted book's, so its Sharpe is
   higher; but `sr0` grows with `N` and `N` is now ~290.
2. **`PBO_NO_SELECTION` will come back LOW (< 0.50)** — 60/40. `current-default` has the WORST
   median OOS IC of the eight candidates (+0.057 against `ic-proportional`'s +0.096), which
   should push its OOS rank DOWN and PBO UP; against that, PBO asks about the median of eight and
   a rank-based statistic on 15 paths is coarse. **This is the expectation I am least sure of and
   the one whose mechanism points against my own answer.**
3. **`X1` A1 (alpha) will come back SURVIVES and A2 (long-short HAC *t*) will also SURVIVE** —
   55/45. On the published universe A1 cleared 200/200 half-books and A2 only 93%; the corrected
   universe's long-short *t* is much stronger (4.59 vs 2.62), which should help A2, and its
   alpha is lower (6.07% vs 7.17%), which should hurt A1.
4. **At least one half-book WILL come back negative on A1** — 65/35. The published run's
   `n_half_books_negative` was 0 of 400 and that was the single most surprising cell in it; a
   universe whose added ~7,100 names are small and dear should produce at least one.
5. **R1's net-of-cost intercept will be POSITIVE and will CLEAR *t* > 2.0** — 70/30, because the
   gross intercept is +5.94% at *t* 4.45 and the one-way-entering-side cost drag is small.
6. **The two-way sensitivity will also clear** — 55/45, and this is the cell that matters for
   whether the "undercharges by ~2×" report changes any verdict.
7. **`V6-B` M1 will SURVIVE its 3.0pp economic floor** — 60/40. It was the largest replicated
   effect this programme has produced (10.8pp, both halves, *t* −10.58) and a wider universe adds
   small names, where `V6-B` measured the separation to be STRONGEST (−14.287pp smallest quintile
   against −3.787pp megacap).
8. **The `N_PANEL_NAMES` stamp will move and P1S0's coverage SHARE will FALL sharply** — 85/15.
   The chain cache is a targeted pull of large, liquid names; 9,645 names is 3.8× the denominator
   and the numerator cannot grow with it.
