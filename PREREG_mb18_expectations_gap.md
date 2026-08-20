# PREREG — MB18: the implied-growth expectations gap

**Registered 2026-08-19. Committed ALONE, markdown only, as a strict git ancestor of every
measurement commit.** Executes `VALQUO_MASTER_AUDIT_4.md` item `MB18`, which it calls *"the
cheapest genuinely-new equity hypothesis in this audit"*.

**1 equity trial, booked BEFORE the run (equity `N` 234 -> 235).**

---

## 0. The hypothesis, in one sentence

`panel_s23_fairvalue.pkl` solves a reverse-DCF `implied_growth` from price and filed fundamentals
**as of the date**, and a `base_growth` from the company's own recent trajectory. The difference —
**how much more growth the price demands than the company has been delivering** — is an
expectations measure at **100.00% coverage over 69 dates**, and nothing in this project has ever
scored it.

**The arm: `exp_gap = implied_growth − base_growth` as a candidate in the incremental-IC gate,
signed NEGATIVE** — high demanded growth relative to trajectory predicts LOW forward returns. The
direction is fixed here, before the run, from the mechanism the audit states (expectations errors:
the path is systematically too optimistic where it is most extrapolated). **A positive result in
the opposite direction is a FAIL, not a discovery.**

---

## 1. THE KILLS, WHICH FIRE BEFORE ANY OUTCOME

### 1.1 LOOK-AHEAD — `realized_growth` may NEVER enter a signal

**`realized_growth` is FORWARD three-year growth.** It is the OUTCOME, not an input. Any arm,
control, filter, standardisation or subsample that touches it is **VOID BY CONSTRUCTION**.

This is pinned **at source, before anything is scored**, by an **AST** test over the measurement
script — reading the syntax tree, not grepping, because `MA49` recorded a fixture that failed
against the FIXED tree since the comment documenting the repair quoted the defect verbatim. The
precedent named by the audit is `MA31`, where `dividends.spot_from_parity` fed back as the spot
would have made the arm **identically zero** and nothing would have raised.

`realized_growth` may appear in **exactly one place**: an ex-post attribution block, computed
**after** the verdict is written and labelled as such. **The gate is that the arm path cannot
reference it at all.**

### 1.2 THE COSTUME KILL — the arm is WITHDRAWN before any outcome at |rho| > 0.60

A reverse-DCF implied growth is monotone in price over fundamentals, so it may be the `value`
theme wearing a new name. **Mandatory control, run and read in its OWN pass before any arm is
scored: mean per-date Spearman of `exp_gap` against the `value` theme.**

> **|rho| > 0.60 -> THE ARM IS WITHDRAWN. No outcome is computed, read, or reported.**

The bar is the audit's own and is **not** negotiable after the number is seen. This control is
**deliberately NOT measured before this register is committed**, which is why it can function as a
kill.

### 1.3 The column-name trap, measured and named so nobody scores the wrong object

**The panel already ships a column literally called `gap`, and it is NOT this arm.** Measured:
`gap` reproduces **`log(fair_value / price)`** at max |delta| **0.000e+00** — a *valuation* gap. The
expectations gap correlates with it at only **−0.5251**. A lookup by name computes cleanly, raises
nothing, and answers a different question — and one much closer to `value`, i.e. the very costume
the arm is being tested against.

**`gap` is FORBIDDEN in the arm path and that is pinned by test**, exactly as `U2` pinned
`term_slope_60_30` out of its own arm.

---

## 2. THE GATE — `MB7`'s re-specified incremental-IC machinery, and the disclosure it requires

`valuation/studies/incremental_ic.py`, landed 2026-08-19 at `96963e7`. Per `RUN_RULES` PART A
rule 10 the register must state its **BASIS** and print its **EFFECTIVE** coverage.

**A structural fact the audit's item does not mention, measured here: `panel_s23_fairvalue.pkl`
carries NONE of the seven incumbent theme columns.** The gate therefore requires an inner join to
`panel_corrected_69d.pkl` on `(date, ticker)`. **Measured: 107,020 rows, 69 dates, 2,432 names —
98.87% of the S23 panel and 93.92% of the theme panel.** `fwd_ret` comes from the **theme** panel,
so the arm is scored against the same forward return every other incremental-IC register uses.

### 2.1 The effective coverage, printed rather than assumed

| basis | effective dates | first effective date | effective rows | split on EFFECTIVE | split on RAW then intersect |
|---|---|---|---|---|---|
| **seven** | **49 of 69** | **2014-01-17** | 65,334 (61.05%) | 24 / 24, boundary 2020-01-22, **ok** | 14 / 34, **NOT ok** |
| **six** (no `institutional`) | **69 of 69** | 2009-01-15 | 91,241 (85.26%) | 34 / 34, boundary 2017-07-20, **ok** | 34 / 34, **ok** |

**`MB7`'s defect reproduces on this panel exactly**: on basis seven the raw split reports 34/34 and
passes the shipped `MIN_DATES = 16` guard while the residualised statistic would be scored on an
**early cell of 14**. The gate refuses that, which is what it was built for.

### 2.2 THE BASIS IS CHOSEN NOW, WITH ITS COST, AND IT IS CO-PRIMARY RATHER THAN PICKED FOR POWER

**PRIMARY: BOTH bases, and the arm must clear on BOTH. Disagreement between them is a NULL.**

Choosing basis six alone would be **choosing the design to buy power**, which is `MA58`'s void
condition 5, and I am not doing it. Requiring both is strictly harder than either.

**The cost of basis six, stated: it does NOT residualise on `institutional`, so an arm clearing it
is not orthogonalised to institutional ownership.** The cost of basis seven: 49 post-2014 dates and
the power below. **Both costs are reported with the verdict or the verdict is not quoted.**

---

## 3. THE POWER STATEMENT, BEFORE THE RUN — `RUN_RULES` PART A rule 11, via `MB22`'s gate

Computed with `valuation/edge/power_gate.py` at **crit = 2.71** (X7's calibrated theme-IC floor,
the bar this arm is judged against) and the 80% power convention:

| basis | effective dates | **MDE at 80% power** | required n for a 0.4346-SD effect | ratio |
|---|---|---|---|---|
| six | 69 | **0.4274 SD** | 66.7 | 1.034 |
| seven | 49 | **0.5071 SD** | 66.7 | 0.734 |

**And the anchor those numbers must be read against.** `U2` recorded that there is **no valid power
control for the INCREMENTAL statistic** — every known-real signal on this panel is already an INPUT
to an incumbent theme, so residualisation removes it by construction. So the control is the **RAW**
IC, which asks whether the date set carries measurable signal at all. Measured on **exactly the
rows this arm will be scored on**:

| anchor | basis six (69 dates) | basis seven (49 dates) |
|---|---|---|
| `z_fcf_margin` | effect **0.4346**, raw *t* **+3.6097** | 0.5880, +4.1163 |
| `z_gp_on_capital` | 0.3776, +3.1367 | 0.3105, +2.1737 |
| `z_ret_6_1` | 0.2060, +1.7110 | 0.3345, +2.3414 |

> **THE HONEST PRE-RUN STATEMENT: this design can detect, at 80% power against the 2.71 bar, an
> effect about the size of the STRONGEST raw signal these rows carry (0.4346 SD on basis six) and
> essentially nothing smaller. On basis seven it cannot even do that.**
>
> **Therefore: a NULL here means "no effect at least as large as the best thing this panel has ever
> carried". It does NOT mean "no effect", and it may never be quoted as one.** Every null is
> reported with the MDE beside it or it is not reported.

**The raw power control PASSES on both bases** — two of three anchors clear 2.71 on six, one of
three on seven — so a null will be interpretable in the `MA58` sense (weak, not blind), while
remaining bounded by the MDE above.

**No second power vocabulary.** `power_gate` prints the 50%-power `detection_threshold` and the
80%-power `mde_at_power` separately, and **this register quotes the 80% figure**; quoting the
smaller one as though it were this is the elision `MB22` exists to stop.

---

## 4. Design — every number fixed now

* **Candidate**: `exp_gap = implied_growth − base_growth`, computed in the script from the two
  banked columns. Both are at 100.00% coverage; the difference is at 100.00% on the joined rows.
* **Sign**: NEGATIVE (declared in §0). A wrong-signed clear is a FAIL.
* **Statistic**: per-date OLS of the candidate on the basis incumbents with intercept, Spearman of
  the residual against `fwd_ret`, *t* across dates. `MIN_NAMES = 20`, `MIN_DATES = 16`, both
  imported from `surface_stock` and never restated.
* **Bar**: **X7's calibrated theme-IC floor of 2.71**, in **BOTH halves**, on **BOTH bases**, with
  the halves split on the **EFFECTIVE** dates.
* **Halves**: `surface_stock.halves` on the effective date list, boundary embargoed.
* **`implied_bounded` is a PARTITION, not a pool.** It is a 3-state solver flag at 100% coverage
  and reads `''` 75,034 / `above` 22,283 / `below` 9,703 on the joined rows — **30.0% of rows hit a
  solver bound.** The arm is scored on **all** rows (the registered primary) and **re-scored on the
  unbounded subset alone as a mandatory sensitivity**. A verdict that exists only on one side of
  that partition is reported as such and does not carry the row.
* **Artifact**: `data/free_analysis/MB18_EXPECTATIONS_GAP.json`, plus `MB18_CONTROLS.json`.
* **Two passes.** `--arms` **refuses** without a controls artifact whose `all_gating_pass` is true.

---

## 5. Controls — C1–C5 GATING, read in their own pass before any arm

* **C1 — LOOK-AHEAD (gating).** An AST walk of the arm path asserts `realized_growth` appears
  **nowhere** in it, and that the arm function's transitive call graph within the script does not
  reference it. Mutation-tested: inserting a reference must fail the test.
* **C2 — THE COSTUME KILL (gating, §1.2).** Mean per-date Spearman vs `value`. **|rho| > 0.60
  withdraws the arm.** Also reported for all seven incumbents, largest |rho| named.
* **C3 — THE `gap` TRAP (gating, §1.3).** The shipped `gap` column appears nowhere in the arm path
  (AST), and the script's own `exp_gap` is asserted **not** equal to it (it must differ; measured
  correlation −0.5251).
* **C4 — POINT-IN-TIME (gating).** Zero rows where the candidate's inputs postdate the rebalance
  date. `S23`'s own offline assertion is inherited: **the run asserts ZERO network calls**, because
  `S23` found that path fetching **live Yahoo prices to value 1999**.
* **C5 — EFFECTIVE COVERAGE (gating).** `require_effective_coverage` must pass on both bases; the
  artifact carries the §2.1 table as computed rather than as typed here.
* **C6 — orthogonality (reported).** R² of `exp_gap` on the basis incumbents. Reported because
  `U2`, `MA31`/`MA32` and `MA58` each found genuinely new information that predicted nothing —
  **orthogonality is not evidence of value, and a high R² is not a kill** (C2 is the kill).
* **C7 — the join is not a universe change (reported).** Row and name counts of the joined frame
  against both parents, and the arm's date set against `S22`'s and `MA58`'s.

---

## 6. My prior, stated before the run

| prediction | odds |
|---|---|
| **the arm clears 2.71 in both halves on BOTH bases** | **8/92** |
| the arm is WITHDRAWN by C2 before any outcome (|rho| vs `value` > 0.60) | 30/70 |
| |rho| vs `value` exceeds 0.40 even if it does not reach the kill | 65/35 |
| the full-sample sign is NEGATIVE as declared | 70/30 |
| the two bases disagree (so the conjunction returns NULL) | 40/60 |
| R² on the incumbents is below 0.15, i.e. genuinely orthogonal | 60/40 |
| the bounded/unbounded partition changes the verdict | 25/75 |

**I am below the audit's ~15%, and the reasons are the record's own rather than instinct.** Three
items in this audit's own lineage were motivated by *"structurally orthogonal to the incumbents"*
and all three failed with R² between 0.027 and 0.088 and nothing to show (`U2`, `MA31`/`MA32`,
`MA58`) — CLAUDE.md now names that motivation as one nobody should run again. Against that: this
candidate is **not** a repackaged price ratio in the way those were, it is at 100% coverage over
the full 69 dates, and the level statistic the project already measured (median implied **0.164**
against realized **0.061**) says prices really do demand more growth than companies deliver. That
is what keeps the prior at 8% rather than lower.

**And the power in §3 caps what a pass could mean anyway:** at 0.4274 SD the design only sees an
effect the size of this panel's best-ever raw signal.

---

## 7. Void conditions — any one voids the verdict

1. **`realized_growth` enters the arm path** in any form (§1.1).
2. **The `gap` column enters the arm path** (§1.3).
3. **C2's 0.60 bar is moved, or the arm is scored after C2 fires.**
4. **The basis is changed after any outcome is read**, or the conjunction in §2.2 is relaxed to
   either basis alone.
5. **The bar is moved off 2.71**, or the both-halves requirement is dropped.
6. **Halves are split on the RAW dates** rather than the effective ones (§2.1).
7. **A null is reported without its MDE** (§3), or the 50%-power figure is quoted as the 80% one.
8. **`implied_bounded` is silently pooled** with no partition reported.
9. **Any network call is made during the build.**
10. **The trial is charged to a domain other than equity, or booked after the run.**
11. **Gating controls are computed in the same pass as any arm.**

---

## 8. What this register CANNOT establish

* **It cannot establish that expectations errors do not predict returns.** §3 bounds it: a null
  covers effects at or above ~0.43 SD and says nothing below.
* **The panel's `fair_value` is `S23`'s RECONSTRUCTION and not what the live site published that
  day** (`MA26-C`). Nothing here is a claim about what users saw.
* **`implied_growth` inherits `S23`'s solver**, including its bounds — hence the mandatory
  partition in §4.
* **It adopts nothing.** No file on a live scoring path is touched, and a pass would be recorded
  `ELIGIBLE`, never adopted: adding a panel input is a construction change and a vintage event.
