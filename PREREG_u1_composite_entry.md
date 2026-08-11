# PRE-REGISTRATION — U1: the equity composite as an options ENTRY signal

**Committed 2026-08-11, ALONE, before `valuation/edge/composite_entry.py`, `scripts/u1_entry.py`
or `scripts/u1_score.py` exist in the tree.** Every threshold, arm, control, statistic and
verdict rule below is fixed here. Nothing in this file may be edited after the first number is
produced; a change of mind becomes a new register with its own trial cost.

This is the first test of whether **the edge the project actually has — the equity composite —
reaches the options book at all.** Everything the options lane has measured for eight sessions
sits inside a book whose *entry* is dead (R2). U1 asks whether a different entry, taken from the
one thing in this project that has survived calibration, does better.

---

## 0. WHY THIS IS BEING REOPENED, AND THE CONDITION IT HAD TO MEET FIRST

`VALQUO_LEDGER.md:300` carries U1 with an explicit blocker, and it is not a stale one:

> **DO NOT RUN AS WRITTEN (2026-08-06, session 6).** U7 was the audit's own 'strictly easier bar'
> for the same hypothesis and it FAILED with a mechanism: on the 187-name options universe the
> composite decile is largely a market-cap sort, so it carries no alert-specific information
> (interaction vs control −0.08pp). **Reopen only with a composite built WITHIN the options
> universe or with size neutralised.**

That is a gate, not a discouragement, and this design clears it **both ways at once** rather than
picking the cheaper one:

* **Within the options universe.** Every ranking below is a percentile computed among the ~182
  optionable names *as of the same rebalance date* — `options_veto._rank_within_universe`'s
  `u7_pct_univ` field, already built and tested for U7. The full-panel percentile is **not** used
  for any arm that carries a verdict.
* **Size neutralised.** The primary null is drawn **matched on market-cap tier per date**
  (`options_universe.tier_of`), so a selection rule cannot clear the bar by preferring a cap
  bucket. U7's mechanism finding is thereby not merely acknowledged — it is *subtracted*.

If the arm clears the plain bar and fails the cap-matched one, **that is U7's finding reproduced
on the entry side**, and it will be reported in exactly those words.

---

## 1. THE CAVEAT THAT TRAVELS WITH EVERY NUMBER IN THIS REGISTER

**R2 stands.** The shipped options alert loses to a five-seed random-entry control (+3.41%/trade
vs +10.06%, date-block CI95 [−11.92pp, −2.13pp], paired name-year sign z −4.903). Nothing here
repairs that. U1 does not rescue the alert; it asks whether a *different* entry works, and a
positive U1 would not make the alert tradeable.

**U1 tests NAME selection, not DAY selection.** The entry grid is fixed to the panel's rebalance
dates and every arm and every null draw shares it exactly. Day selection is already measured and
dead (R2), so holding the calendar fixed is deliberate: it removes the dead question from the
live one instead of re-asking it.

**The composite's own horizon is the wrong shape for an option and this is known in advance.**
S22 measured that the composite's rank IC *rises* with horizon (+0.034 at 63d → ~+0.072 at
two years) — so the weakest point on that curve is the short end, and a 30–75 DTE contract lives
at the short end. U1 is therefore a test of the composite where the composite is *least* strong.
A NULL here does not refute S22 and may not be quoted as if it did.

---

## 2. THE CORPUS, FIXED NOW

| | |
|---|---|
| Panel | `data/free_analysis/panel_corrected_69d.pkl` — the corrected 69-date panel, 113,945 rows, 2,531 names |
| Rebalance dates in the options window | **39**, 2016-01-20 → 2025-07-29 (window `ENTRY_START` 2016-01-01 → `ENTRY_END` 2025-10-15) |
| Options universe | the **182** names that are both in the R2 book's 186 and present in the panel. The four dropped (`AMAT`, `RIO`, `SHEL`, `UBS`) are named here so the loss is on the record, not discovered later |
| Chains | `data/options/` via `theta_bulk.ThetaBulk` — local, offline, read-only |
| Bars | `data/bulk/prepared/bars` via `options_backtest.load_bars` |
| Alert book (comparison arm) | `data/options_universe/state_r2_corrected.pkl`, 3,885 trades / 186 names |
| Random-DAY reference | `data/options_universe/control_r2_seed{0..4}.pkl`, the five-seed R2 control |

**The full grid is every (name, date) cell: 182 × 39 = 7,098 candidate entries.** It is mined
ONCE. Every arm and every null draw below is a **subset of that one mined grid**, so no arm can
differ from another by anything except which cells it selected — not by fill, not by contract,
not by exit, not by calendar.

---

## 3. THE ENTRY RULE (exact, and it is the part that can silently be wrong)

For each rebalance date `d` of the 39, and each of the 182 names:

1. **The composite is the as-of one, never the enclosing one.** The composite attached to an
   entry comes from the most recent rebalance date **strictly ≤ the entry date** —
   `options_veto.as_of_index`, the join built and tested for U7, reused unchanged. The
   *enclosing* rebalance would score an entry with filings that were not public when it was
   taken; that is up to a full quarter of look-ahead and it would flatter every number here.
2. **The entry day is the first trading day STRICTLY AFTER `d` on which a chain exists.**
   Entering on `d` itself would satisfy "≤" only at the boundary; stepping one day past it makes
   the inequality strict with no argument, and costs one day of a ~45-day trade.
3. **The contract, the fill and the exit are the shipped ones, CALLED not copied.** The exact
   sequence from `options_universe.random_entry_control` — `bars_asof` → `spot_asof` (as-traded,
   per B1) → `OB.pick_contract(chain, und, day, right="C")` → `OB.simulate_trade(...,
   aggression=1.0)` → `OB.to_alert_row(...)` — plus the O20 point-in-time liquidity fields and
   the cap tier. **The exit policy is +100% target / −50% stop / half-DTE time stop and is not
   touched**: S23 and the path study both say leave it, and TP-BAR closed the one open question
   about raising it (REJECTED on the calibrated bar, 2026-08-11).
4. A cell that yields no chain, no contract in band, or no simulable trade is **dropped and
   counted**, never imputed.

**Ranking.** Within each date, the surviving cells are ranked by composite **among the options
universe only**, percentile 0.0 = worst … 1.0 = best (the `u7_pct_univ` convention).

---

## 4. THE ARMS

| arm | selection | role |
|---|---|---|
| **GRID** | every surviving cell | the benchmark every gain is measured against |
| **TOP10** | `pct_univ >= 0.90` | **the primary arm** |
| **TOP20** | `pct_univ >= 0.80` | secondary, pre-registered, not a fallback for a failing primary |
| **BOT10** | `pct_univ <= 0.10` | the contrast; a real signal should make this *worse* |
| **DECILES** | all ten | mechanism, reported whatever the verdict |

`gain = mean(arm) − mean(GRID)` in percentage points of per-trade P&L. Measured on the **same
dates**, so a gain cannot come from the arm having found better quarters.

---

## 5. THE CONTROLS AND THE CALIBRATED BARS

**The null is not a no-effect null and that is stated here in advance** — the same distinction
TP-BAR turned on. Every draw is a real book of real trades on the real grid; the null therefore
*contains* whatever the grid earns. Its p95 answers **"is this selection rule distinguished among
selection rules of its own size?"**, not "does selecting names do anything".

* **NULL-PLAIN** — 200 draws. Each draw selects, **per date**, the same number of cells the real
  arm selected on that date, uniformly at random from that date's surviving cells. Date
  composition is held **exactly** fixed.
* **NULL-CAPMATCHED** — 200 draws. As above, but within each date the draw matches the real arm's
  **market-cap tier histogram** (`tier_of`), sampling within tier. **This is the size-neutralised
  bar and it is the ledger's reopen condition.** Where a tier has too few cells to match, the
  shortfall is filled from the nearest tier and the number of such fills is reported.
* **SEEDS-5** — the five draws with seeds 0–4 from NULL-PLAIN, **pooled**, reported separately as
  the register's ≥5-seed random control. It is a subset of the 200 and is reported because five
  pooled seeds is this project's standing options control convention (R2), not because it is the
  bar.
* **CALIBRATED BAR** = the **95th percentile** of the 200 draws' gains, computed for each null.
  Two bars, both fixed by this document before either is known.

**These bars are computed and committed in their own commit, with the scoring module not yet
written, exactly as TP-BAR C1 was.** The scorer will read them from the artifact and refuse to
run if the artifact disagrees with the figure published in the follow-up section of this file.

---

## 6. THE STATISTICS

* **Date-block bootstrap**, calendar-month blocks, paired — `options_veto.fast_block_diff`, which
  is the exact-rewrite of `options_stats.date_block_diff` pinned by a test. A drawn month
  contributes to both arms, so common calendar variance drops out. 4,000 draws.
* **Paired name-year sign test** — `options_stats.paired_name_year`, R2's standing rule: the sign
  test carries the options verdict, the paired *t* does not.
* **Design effect** must be reported with its shuffled null (R3's lesson: a raw design effect is
  not evidence of clustering).
* **Halves** — the 39 dates split 20/19 at the median date; the gain is reported on each.

---

## 7. THE VERDICT RULE (mechanical, fixed now)

**PASS** — "the equity composite reaches the options book" — requires **ALL FOUR**:

* **V1** TOP10 gain **>** the NULL-PLAIN calibrated bar.
* **V2** TOP10 gain **>** the NULL-CAPMATCHED calibrated bar. *(the ledger's condition)*
* **V3** the paired date-block CI95 on `TOP10 − GRID` **excludes zero on the positive side**.
* **V4** the TOP10 gain is **positive in both halves** of the window.

**REJECTED** if the TOP10 gain is **negative**, or the decile table's expectancy trend runs the
wrong way (best decile below worst) — i.e. the composite actively misinforms the options book.

**NULL** in every other case, including "positive but does not clear a bar". **Ambiguous is a
NULL** — per the instruction opening this work, and per session 8's rule that a near miss is a
null and "decoration" is the wrong word for it.

**No third state, and no re-park.** U1 closes on this run with one of PASS / NULL / REJECTED.

**What a PASS would and would not license.** It would be a research finding about an entry rule,
on one panel, gross of the paper book's own frictions, on a 39-date grid. It would **not** ship
anything: adopting it into the live options bot is a construction change that needs its own
register, and the paper-track contract binds the **Index**, not this book.

---

## 8. THE EXPECTATION, WRITTEN BEFORE ANY NUMBER EXISTS

Scored against the result in the follow-up section, as the house style requires. This project's
directional calls have been wrong far more often than right, which is the reason they are
recorded.

| # | prediction | confidence |
|---|---|---|
| **E1** | **Verdict is NULL** — positive point estimate, does not clear both bars | 60/40 |
| **E2** | TOP10 gain lands in **0 to +4pp** | 55/45 |
| **E3** | **NULL-CAPMATCHED is the binding constraint** — if V1 passes, V2 fails | 65/35 |
| **E4** | The decile table is **not monotone** (U7 found it U-shaped on alerts) | 60/40 |
| **E5** | The GRID book **beats the alert book** per trade — i.e. entering everything quarterly beats the alert, because R2 already showed random entry beats it | 70/30 |

**E5 is the one worth watching.** If it holds it is a restatement of R2 in a new corpus and costs
the alert nothing further; if it fails it would be the first evidence in eight sessions that the
alert's entry is *not* uniformly dominated, and that would be more interesting than U1's own
verdict.

---

## 9. TRIAL COST, COMMITTED IN ADVANCE

* The **grid mine** is data construction and searches nothing: **0 trials.**
* The **two calibrations** (NULL-PLAIN, NULL-CAPMATCHED) are calibrations, not searches:
  **0 trials**, on the X7 and session-10 HAC-floor precedent.
* The **arms** TOP10, TOP20, BOT10 are three scored selection rules: **3 trials.**
* The decile table is descriptive and carries no verdict: **0 trials.**

**Options `N` 207 → 210.** Equity `N` is untouched by this work; it reads 143 and must be
re-read from `research_log.detail()` rather than copied from here if it is quoted anywhere.
