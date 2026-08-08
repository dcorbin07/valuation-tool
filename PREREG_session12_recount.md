# PRE-REGISTRATION — Session 12: the trial-counter repair and the recount

**Committed BEFORE the parser is touched and before any corrected count is computed.**
Written 2026-08-08, audit session 12. The point of this file is that a recount which changes `N`
changes the significance of every DSR-gated claim in the project, so the recount must not be
steerable by its own consequences. What follows fixes the procedure in writing first.

---

## 0. The baseline, as shipped right now

Measured before any change, from `research_log.detail()` on `RESEARCH_LOG.md` at `8c1e524`:

| scope | trials | note |
|---|---|---|
| **equity** | **129** | the denominator the composite's Deflated Sharpe is charged |
| options | 155 | |
| unified | 0 | |
| infra | 3 | |
| **total** | **287** | |
| rows counted | 55 | |
| rows dropped as `FIXED` | 17 | |

Shipped equity statistics at N = 129: **Deflated Sharpe 0.8556**, √(2·ln 129) = **3.1176**.

## 1. The defects, identified by READING THE CODE, before any recount

All three are the same class — **a field is read by searching text that is not that field.**

1. **THE NAMED ONE (`research_log.py:72-73`).** `verdict = " ".join(cells).upper()` joins *every*
   cell of the row and then tests `re.search(r"\bFIXED\b", ...)`. A row whose hypothesis, metric,
   threshold, source or free-text note contains the word "fixed" is dropped from `N` even though
   its verdict column says `ADOPTED` / `REJECTED` / `NULL`. **Direction of error: understates `N`,
   which OVERSTATES significance.** Carried three sessions; worked around by wording, which means
   the shipped `N` is currently protected by agents choosing synonyms.
2. **THE GRID MULTIPLIER (`research_log.py:77`).** `re.search(r"\bn=(\d+)\b", ln)` searches the
   **whole line**, not the `n` column. Any prose containing `n=100` (a draw count, a seed count, a
   sample size — all of which this project writes constantly) would multiply that row's trial
   count. **Direction of error: either way**, and silently.
3. **THE DOMAIN (`research_log.py:83-86`).** `any(c.lower() == d for c in cells)` scans `DOMAINS`
   in order `(equity, options, unified, infra)` and takes the first domain matching *any* cell, not
   the domain column. A row whose domain is `options` but which has some other cell equal to the
   bare word `equity` is charged to equity. **Direction of error: either way**, and it moves
   trials between families, which is exactly what a BH-FDR family boundary must not do.

`RESEARCH_LOG.md` contains **two tables with different column layouts** — the original at line 81
(`id date domain hypothesis universe metric threshold verdict source`, verdict at index 7) and the
retrospective reconstruction at line 128 (`id date domain pre hypothesis metric verdict n source`,
verdict at index 6, `n` at index 7). Any fix that hard-codes a column index is a fourth bug.

## 2. THE FIX, specified before it is written

Resolve columns **from each table's own header row**: walk the file top to bottom, and when a
markdown header row is seen, record the index of the columns whose names are `verdict`, `n`,
`domain`, `id`. Every data row is then parsed against the header currently in force, and each
field is read **only from its own column**.

- The `FIXED` test reads **the verdict cell alone**, and matches only when that cell's text
  *begins* with `FIXED` (so the existing legitimate value `FIXED (relabel only)` still counts as
  fixed, while a verdict of `REJECTED` in a row that merely mentions fixing something does not).
- The grid multiplier reads **the `n` cell alone**; absent that column, `k = 1`.
- The domain reads **the `domain` cell alone**; an unrecognised domain is counted in the total and
  in no family.

## 3. AMBIGUITY RESOLVES TOWARD A LARGER `N` (RUN_RULES A6)

A larger `N` is the less favourable direction: it raises every bar the project must clear. So:

- a row whose table has **no resolvable header** is parsed by the current whole-row rule for
  `FIXED` **only if that makes it count**; if the whole-row rule would drop it and the column rule
  cannot be applied, **it counts**;
- a verdict cell that is **empty or unreadable** counts as a trial, not as `FIXED`;
- an `n` cell that is present but unparseable is `k = 1` — never dropped to `k = 0`.

## 4. WHAT COUNTS AS A CHANGED VERDICT (the thing that must not be steerable)

A **row moving in or out of `N`**, or its `k` or its family changing:

- **IN**: old parser dropped it as `FIXED`; corrected parser finds a non-`FIXED` verdict column.
- **OUT**: old parser counted it; corrected parser finds `FIXED` in the verdict column.
- **RE-WEIGHTED**: `k` differs between the whole-line grep and the `n` column.
- **RE-FAMILIED**: the domain column differs from the first-matching-cell scan.

**THE CORRECTED PARSE IS AUTHORITATIVE WHICHEVER WAY `N` MOVES.** If `N` falls — making every
threshold easier — that is published with the same prominence as a rise, and no row is re-worded
to prevent it.

**NO ROW'S TEXT IS EDITED THIS SESSION FOR THE PURPOSE OF CHANGING `N`.** The parser is repaired;
the log is not rewritten to preserve or improve a number. If the recount surfaces a row that looks
*mislabelled* — a genuine search recorded as `FIXED`, or a bug fix recorded as a trial — that is
**reported as a finding and left in place**, because re-labelling rows while looking at their
effect on the denominator is the same error one level up. A future session may re-adjudicate it
against the schema, not against the arithmetic.

**Every changed row is published individually** — id, old treatment, new treatment, the cell that
caused it — so the recount can be checked by hand rather than believed.

## 5. IF `N` MOVES, WHAT GETS RESTATED

Mechanically, via `ablation.deflated_sharpe_at(detail, n_trials)` — the same function used to move
a recorded statistic to a new `N` in sessions 9 and 11 — reading the shipped
`deflated_sharpe_detail` from the corrected 69-date panel. Restated: the equity Deflated Sharpe,
√(2·ln N), and every claim quoting either.

**Claims to re-check by name, each with its outcome published whether or not it changes:**

1. X7's calibrated Deflated Sharpe floor (**0.7216**) and the "sits above all 100 placebo draws"
   reading — note in advance that a *calibrated floor* is a property of the placebo distribution,
   not of `N`; what can move is the shipped statistic compared against it.
2. Session 10's HAC floor (**2.2837**) and the headline's margin over it — the long-short *t* is
   not a function of `N` at all; this is checked to confirm that, not because it is expected to
   move.
3. Session 11's ML-combiner verdict framing (`N` 121 → 129, DSR 0.8628 → 0.8556).
4. Session 9's SELRULE figures (`N` 116 → 121, DSR 0.8628).
5. M1's own table (N = 8 vs N = 84) and the `CLAUDE.md` bullets quoting equity 116 / 0.8674.
6. The Harvey–Liu–Zhu 3.0 hurdle comparison.

A claim whose number changes is corrected **in place, in the house convention** (the old text
quoted, marked corrected, with the date and the reason) rather than deleted.

## 6. ITEM 3 — the X7 7%-vs-8% discrepancy, and what counts as diagnosed

Session 10 re-ran X7's placebo with the same seeds and got `ls_t ≥ 2.0` on **7** of 100 draws
against X7's recorded **8**, with no draw near the 2.0 boundary (nearest 1.885 and 2.067), and
recorded it as undiagnosable because X7's raw draws were never retained. Session 10's draws **are**
retained (`data/free_analysis/PLACEBO_HAC.json`).

- **DIAGNOSED** requires naming the specific mechanism and showing it accounts for exactly one
  draw — e.g. an identified draw whose naive `ls_t` sits on the far side of 2.0 under one code
  path and not another, reproducible on demand.
- **STILL NOT DIAGNOSABLE** requires stating precisely *what* would be needed and *why* it does not
  exist, with the retained draws in hand — not a repetition of "the draws were never saved".
- **A plausible story is not a diagnosis.** If the cause can only be inferred rather than shown,
  it is recorded as a hypothesis and labelled one.
- **Zero trial cost either way**: reconciling a recorded rate against retained draws searches
  nothing and produces no new claim about the strategy.

## 7. EXPECTATION, WRITTEN FIRST

**Equity `N` rises, 60/40, and by a small amount (0–6).** Reasoning: the `FIXED` defect strictly
understates, so any historical row containing the word "fixed" in prose is currently missing; but
the last three sessions knew about the defect and dodged it by wording, so the loss should be
confined to rows written before 2026-08-06. I expect the `n=` and domain defects to be latent
rather than live — real, but not currently firing on any row.

**If the expectation is wrong, that is recorded as another entry in this project's long run of
wrong directional calls, not quietly dropped.** (The record on this is four wrong, one right.)

## 8. TRIAL COST

**Zero.** Repairing a parser and recounting rows searches no data and tests no hypothesis about
returns. It is logged as `infra` with `FIXED`, consistent with the schema's own rule that a
correctness repair is not a trial — the rule this session is making the code actually implement.
