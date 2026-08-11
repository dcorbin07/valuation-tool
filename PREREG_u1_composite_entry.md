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

**Options `N` 207 → 210.** Equity `N` is untouched by this work. **It reads 149, not the 143 this
file said when section 9 was written** — S23's six arms landed from another lane while U1 ran,
and a stale `N` overstates every DSR-gated claim, so it is corrected here rather than left.
Always re-read it from `research_log.detail()`.

---

## 10. AMENDMENT 1 — `U1-SPLIT`: a corporate-action defect, found during calibration, **before any arm was scored**

**Added 2026-08-11, in the same commit as the bars, with `scripts/u1_score.py` not yet written.**
That ordering is checkable from git and is the only reason this amendment is legitimate rather
than a renegotiation: **no arm's gain existed, anywhere, when this rule was written.** Sections
0–9 above are unedited.

### What it is

The ThetaData option chains are **as-traded and unadjusted for splits**; `bars` (Sharadar SEP)
**are** adjusted. Nothing in the options lane has ever consulted the split table, although
`valuation/edge/bulk.py:312` documents the hazard in so many words — *"an unadjusted split looks
[like a huge move]"*.

The signature is a **reverse** split. **GE split 1-for-8 on 2021-08-02.** A $14-strike call
bought 2021-07-23 at **$0.27** settles at expiry against a ~$104 post-split underlying on a
strike that was never re-based, and books **+31,921%**. That single row is **6.28pp of the
5,186-trade grid's 9.93% mean** — 62% of the grid's entire expectancy, from one trade in 5,186.

Forward splits do **not** show the signature (AAPL 4:1 → +236%, NVDA 10:1 → +225%, AVGO 10:1 →
+290% are all plausible), so this is **not** a claim that every split is corrupt. It is that a
trade whose contract life crosses one **cannot be verified** and must not be scored.

### The rule, and why it cannot select on the outcome

Exclude any trade for which a split with ratio ≠ 1 falls in `(alert_ts, expiry]`, per
`composite_entry.spans_split`. **Defined by an external table and a date comparison — never by
the size of a return.** A rule that dropped "implausibly large" P&L would be selecting on the
outcome, which is exactly what a null exists to forbid. The window is the **contract life**, not
the realised holding period: an exit is priced off a quote series the split has already
corrupted, so the wider window over-excludes by a handful of rows and under-excludes by none.

It is applied to the **GRID**, so every arm and every null draw inherits it — they are subsets
and cannot reintroduce a row the grid does not have. **18 of 5,186 rows (0.35%).**

### Both bars are retained, and the verdict basis is fixed here

| basis | TOP10 plain | TOP10 cap-matched |
|---|---|---|
| **SPLIT_CLEAN — the verdict basis** | **+7.2870pp** | **+9.4513pp** |
| RAW (uncorrected, kept for the record) | +59.9628pp | +62.8077pp |

Both are in `data/options_u1/U1_NULL.json`. Neither has been compared to an arm.

### THIS IS A CROSS-LANE BUG AND IT MOVES A PUBLISHED HEADLINE

Measured on the banked books, not inferred:

| book | as published | split-clean | move |
|---|---|---|---|
| R2 alert book | +3.4103%/trade | +3.2702% | −0.1401pp (15 rows) |
| R2 five-seed control | +10.0571%/trade | +8.3342% | **−1.7229pp** (131 rows) |
| **R2 gap** | **−6.6468pp** | **−5.0640pp** | **24% of the published gap is an artifact** |

**The control is contaminated ~12× harder than the alert book** because it draws many random days
per name-year and therefore gets many more shots at any given split window (two GE reverse-split
draws at +269x and +261x). **So the defect has been making R2's negative verdict look WORSE than
it is, and correcting it runs toward the alert.** R2's sign, significance and verdict are
**unchanged** — the alert still loses decisively — but anyone quoting "−6.65pp" should quote
**−5.06pp** once this is repaired at source.

**Owner: the options lane (this one) for the corpus, but the repair belongs upstream in the
miner/replay path, not in U1.** U1 excludes; it does not re-price. Filing this is `RUN_RULES`
rule 3 — report every bug, including outside your lane — and the direction it ran is stated
because it is the flattering-to-nobody one.

### Expectation E6, recorded now and scored later

**E6: the split-clean grid mean is +3.65%/trade, so the GRID still beats the alert book's
+3.27% split-clean — E5 survives the correction, but narrowly, at 60/40.** Written before the
arms were scored, like the rest.

---

## 11. THE RESULT — `U1` closes **REJECTED**

Run 2026-08-11 against the bars committed at `e34dc9d`, which contains no scorer.
`data/options_u1/U1_VERDICT.json`; reproduce with `python -m scripts.u1_score`.

### The verdict table

| | TOP10 | TOP20 | BOT10 |
|---|---|---|---|
| n trades | 486 | 948 | 557 |
| mean / trade | +2.4624% | +4.6726% | +11.3446% |
| **gain vs grid** | **−1.1892pp** | +1.0210pp | +7.6930pp |
| **V1** vs plain bar | **FAILS** (+7.2870) | FAILS (+4.6411) | clears (+5.9833) |
| **V2** vs cap-matched bar | **FAILS** (+9.4513) | FAILS (+5.3309) | clears (+5.5733) |
| percentile in its own null | **31st / 15th** | 63rd / 48th | 99th / 99th |
| **V3** date-block CI95 | **FAILS** [−11.74, +10.29] | FAILS [−6.24, +8.42] | FAILS [−1.53, +17.26] |
| **V4** both halves positive | **FAILS** (+5.18 / −5.61) | passes (+0.14 / +1.50) | passes (+1.13 / +12.47) |

**TOP10 fails all four conditions and its gain is NEGATIVE, so the rule fires REJECTED.** The
grid it is measured against is 5,168 trades over 39 dates and 181 names, mean **+3.6516%/trade**.

### The mechanism, and it is cleaner than the verdict

**Every decile's MEDIAN trade is between −52.5% and −54.3%. All ten.**

| | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| mean | +2.46 | +7.00 | +6.98 | +4.67 | +1.92 | +5.03 | +2.60 | −0.09 | −4.89 | +11.35 |
| median | −52.8 | −52.9 | −52.5 | −52.9 | −53.0 | −52.5 | −53.3 | −53.3 | −54.3 | −52.6 |

**The composite does not move the typical option trade at all.** Every difference between deciles
lives in the right tail — and the right tail on ~500 trades is precisely what a +7.29pp bar says
is noise. **TOP10's own mean is entirely tail-carried: its best five trades contribute +3.912pp
of a +2.462% mean, i.e. 158.9% of it.** Remove them and the arm is negative outright; winsorised
at its own p99 the gain worsens to **−1.4911pp**.

### Reported because it is the strongest number and it cuts AGAINST the composite

On the **paired name-year sign test — R2's standing rule that the sign test carries the options
verdict** — the composite's top names are **significantly worse** than the same universe's other
cells. The comparison is within `(ticker, year)`, so it asks: for the same name in the same year,
did the quarters it ranked top-decile produce better option trades than the quarters it did not?

* **TOP10: 119 of 285 cells won, 41.8%, z −2.7840, p 0.0054**
* **TOP20: 210 of 489 cells won, 42.9%, z −3.1203, p 0.0018**

Two arms, same direction, the wider one stronger. **Stated with its limit: no calibrated bar
exists for this statistic** — X7 and session 10 calibrate levels, not paired within-grid sign
tests — so the p-values are **conventional and uncalibrated**, and this is one of three arms.

### `BOT10` CLEARS BOTH BARS AND IS **NOT** A FINDING. DO NOT ACT ON IT

The worst-composite decile gains **+7.6930pp**, sits at the **99th percentile of both nulls**, and
survives winsorising (+7.4869pp). It is nonetheless refused, on grounds fixed before the run:

* its **date-block CI95 includes zero** [−1.53, +17.26] — it fails V3, the same condition TOP10
  fails;
* it is **carried by the late half** (+1.13 early vs +12.47 late);
* its **sign test is 52.0%, z +0.7256, p 0.4681** — it does **not** win more often, it wins
  *bigger*. A mean-only effect on 557 trades with a flat median is a tail statement;
* it is the **extreme of three arms**, and the register attaches a verdict only to TOP10.

**Calling this "the composite runs backwards" would be the exact error TP-BAR closed** — reading
a region of a noisy corpus as a location. The decile table is **UNORDERED, not INVERTED**: D9 is
the worst cell (−4.89%) and D10 the best (+11.35%), which no monotone story explains. The
mechanical `backwards` clause did fire (D1 < D10) and is recorded, but **"inverted" is the wrong
word and must not travel** — the negative gain alone was already sufficient for REJECTED.

### E5/E6 confirmed: the mechanical quarterly grid beats the dead alert, and both lose to random days

| book (all split-clean) | n | mean/trade |
|---|---|---|
| **U1 GRID** — every name, every quarter | 5,168 | **+3.6516%** |
| R2 alert book | 3,870 | +3.2702% |
| U1 TOP10 | 486 | +2.4624% |
| R2 five-seed random-DAY control | 29,654 | +8.3342% |

**GRID beats the alert by +0.3814pp; TOP10 LOSES to it by −0.8078pp.** So a rule that ignores the
alert entirely and buys everything quarterly does better than the alert — R2 restated in a fresh
corpus — while the composite-selected subset does *worse* than the alert. **Both are far below
random-day entry (+8.33%)**, which is not a paired comparison — the control samples days across
the whole year while the grid is locked to 39 fixed dates — but it does say the quarterly grid's
date concentration is expensive, and it is reported rather than omitted.

### The expectations, scored: **3 right, 2 wrong, 1 untriggered**

| | prediction | outcome |
|---|---|---|
| E1 | NULL at 60/40 | **WRONG** — REJECTED |
| E2 | gain 0 to +4pp at 55/45 | **WRONG** — −1.1892pp |
| E3 | cap-matched binding *if* V1 passes, 65/35 | **UNTRIGGERED** — V1 failed, so the conditional never fired. Its spirit held: the cap-matched bar is higher (+9.45 vs +7.29) and TOP10 sits lower inside it (15th vs 31st percentile) |
| E4 | decile table not monotone, 60/40 | **RIGHT** |
| E5 | grid beats the alert book, 70/30 | **RIGHT** — +0.3814pp |
| E6 | E5 survives the split correction, narrowly, 60/40 | **RIGHT** — and it was narrow |

### What this does NOT say

* **It does not refute the equity composite.** S22 measured that the composite's rank IC *rises*
  with horizon (+0.034 at 63d → ~+0.072 at two years); a 30–75 DTE contract lives at the *short*
  end, where the composite is weakest, and it was pre-registered in section 1 that U1 tests the
  composite where it is least strong. The equity book's +6.6%/yr top-decile alpha is untouched.
* **It does not say name selection is hopeless in options** — it says *this* composite, at *this*
  horizon, on *this* 182-name megacap universe, at a quarterly grid, carries no information about
  the median option trade. A composite built **within** the options universe from options-native
  inputs remains untested and is U2's territory, not U1's.
* **It does not rescue or further damn the alert.** R2 stands, at a corrected gap of −5.06pp.

### Trial cost, as committed

Three scored arms: **options `N` 207 → 210.** The grid mine and both calibrations are charged
**zero** (X7 / session-10 HAC-floor precedent). Equity `N` untouched at **149** (re-measured, not copied: it was 143 when this register opened).
