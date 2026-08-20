# PREREG DRAFT — SC-1: were this project's stated priors calibrated?
## The register-calibration study: scoring ~550 trials' own pre-registered expectations

**DRAFT, written by the Frontier Scout lane 2026-08-20. Not committed as a register.** An
executing lane that adopts it must commit it ALONE (markdown only, zero `.py`), as a strict git
ancestor of every measurement commit, after re-reading the live counters — the numbers below
are at equity 234 / options 305-reported / infra 17 and go stale the moment anything lands.
The executor may reject this draft; that is the system working.

**Trial charge: 1, infra (17 → 18), booked BEFORE stage 1 runs.** The `R4` precedent governs:
accounting over existing measurements searches no new data, and charging equity or options
would double-count the very trials being studied. Infra `N` gates no published claim.

---

## 0. Blindness, stated exactly (the MB22 §0 convention)

This study is **not blind in the ordinary sense and pretending otherwise would be worse than
saying so.** Anyone who has read this record — the scout who drafted this, the executor who
runs it — has seen many individual outcomes. What nobody has seen, because it has never been
computed, is any **aggregate**: the Brier score, the calibration gap, the shrinkage
distribution, the feature associations. Three protections stand in for blindness:

1. **The extraction is mechanical from written text**, governed by §2's rules fixed here, and
   is double-entered on a random sample (§2.4) so a reader's memory of outcomes cannot quietly
   steer inclusion.
2. **Every bar and every verdict state is fixed in this document** before any aggregate exists.
3. **The per-pair table ships with the result** (rule 9: the pairs are the draws), so any
   claimed aggregate is recomputable by anyone from the banked rows.

---

## 1. The objects

* **A scoreable pair** = (a numeric prior `p` stated in a register/audit item **before** its
  run, attached to a pre-named binary event `E`; the adjudicated outcome `y ∈ {0,1}` of `E`).
  `NN/MM` odds convert as `p = NN/(NN+MM)`; `Prior: ~X%` converts as `p = X/100`; a prior
  stated only in words ("expect NULL") is **not scoreable** and is counted, not scored.
* **Universe of sources, closed and named:** the `PREREG_*.md` files (71 at this writing; 63
  carry expectation sections, 36 carry numeric odds), the four audits' item priors (13
  `Prior: ~` lines in `VALQUO_MASTER_AUDIT_4.md` alone), the `DESIGN_*.md` records, and the
  self-scored `Expectations N right, M wrong` statements in `CLAUDE.md` and `HANDOFF_*.md`
  (22 at this writing) **used only for adjudication**, never as priors. Nothing else. No
  market data, no panel, no chain, no price is read anywhere in this register.
* **Adjudication order, fixed:** (1) the item's own write-up scoring its expectations
  explicitly (right/wrong/unresolved/split); (2) failing that, the ledger verdict cell where
  the event's own words match it; (3) failing both, **excluded as UNRESOLVABLE** and counted.
  `unresolved`/`split` scorings are excluded and counted (the `O21-D2` "1 unresolved"
  precedent: a filter that ran and found nothing must not read the same as one that never ran).

## 2. Stage 0 — extraction (descriptive; runs before the trial is booked)

2.1 One row per expectation statement: `source_file, item_id, commit_of_register, date,
domain, p, event_text_verbatim, class, outcome, adjudication_source`.

2.2 **Class taxonomy, fixed:** `OUTCOME` (the event is a measured result crossing a stated
bar/direction), `MECHANISM` (why-it-works claims), `INSTRUMENT` (a control/port reproduces),
`PROCESS` (something about the run itself). Primary analysis uses **OUTCOME only**; the other
classes are scored and reported as declared secondaries.

2.3 **Inclusion is textual, not judgemental:** the event must be stated in the same table row
or sentence as the odds. If the executor must infer what was predicted, the row is excluded
as AMBIGUOUS and counted.

2.4 **Double entry.** A second, independent pass re-extracts a 20% random sample
(`seed = 20260820`). Disagreement rate on (p, class, outcome) is reported.

2.5 **Pre-outcome kill (the MB15 pattern — fires before any aggregate is read):**
if scoreable OUTCOME pairs number **fewer than 25**, or double-entry disagreement exceeds
**15%**, the calibration leg is **CANNOT-TELL BY CONSTRUCTION**: only the extraction table and
counts ship, no Brier is computed, and the trial is still charged (the search was run).

## 3. Stage 1 — calibration (the trial)

3.1 **Primary: calibration-in-the-large.** `gap = mean(p) − mean(y)` over OUTCOME pairs, with
a **cluster bootstrap CI95, clustered by register file** (pairs within one register share an
author-session and are not independent; the clustering is pinned by showing it widens the
interval on the real clusters vs a naive resample).

* **OVERCONFIDENT-OPTIMISTIC** if `gap > 0` and CI95 excludes 0.
* **OVERCONFIDENT-PESSIMISTIC** if `gap < 0` and CI95 excludes 0.
* **CALIBRATED-IN-THE-LARGE** if CI95 includes 0 **and** its half-width ≤ 0.15 — a wide
  interval containing zero is CANNOT-TELL, never "calibrated".

3.2 **Secondary, declared:** mean Brier with the same cluster CI; **Brier skill vs two fixed
comparators** — the in-sample base-rate forecaster (predicts `mean(y)` for every pair; the
convention of the replication-forecasting literature) and the uniform 0.5 forecaster; Murphy
decomposition (reliability / resolution / uncertainty); reliability curve in **three bins
fixed now**: p ≤ 0.25, 0.25 < p ≤ 0.60, p > 0.60 (reported, no verdict — bin counts will be
small and the register says so).

3.3 **Era split, reported (no verdict):** pairs split at the median register date — did
calibration move as the discipline matured?

## 4. Stage 2 — the shrinkage arm (same trial, fixed here)

4.1 Universe: every trial whose write-up banked the **same registered primary statistic** on
(a) a decide half and a measure half, or (b) a full sample and both halves. Class (a) is the
**selection-shrinkage** set (primary here); class (b) is the **stability** set (secondary).

4.2 Statistics, fixed: for (a), `r = effect_measure / effect_decide` per trial; deliverable =
median `r` with bootstrap CI over trials, plus the sign-agreement rate. For (b),
sign-agreement between halves and median `|late|/|early|` where `|early|` exceeds the
write-up's own reported uncertainty (else excluded, counted).

4.3 **No bar.** The arm is distributional. **One rule-consequence pre-committed instead of a
verdict:** if the class-(a) median `r` lands below **0.7**, a proposal goes to Don (not
auto-adopted) that `RUN_RULES` A-11 power lines additionally state power at `r×` the expected
effect. If it lands below **0.5**, the proposed factor is 0.5. Nothing retroactive.

## 5. Power, stated before anyone runs (rule 11)

With `n` scoreable OUTCOME pairs and per-pair Brier variance bounded by 0.25 (realistically
≈0.09 for probabilities in the 0.1–0.6 range this record states), the detectable
calibration gap at |t| ≥ 2 is approximately `2·sqrt(0.09/n)·k` (k the cluster inflation,
expected 1.2–1.6): ≈ **0.12–0.16 at n = 36** and ≈ **0.08–0.11 at n = 76** (50%-power
figures; 80%-power ≈ 1.42× those — the MB22 vocabulary, and both numbers are quoted because
this project has historically published only the first). The executor prints the exact line
from `power_gate.state()` on the realized n **before** reading any aggregate. **This design
resolves a coarse question — "materially miscalibrated or not" — and cannot resolve bin-level
shape. It says so here so a null cannot be read as "calibrated everywhere".**

## 6. Controls

* **C1 — fixture round-trip:** the scoring code reproduces hand-computed Briers on five
  synthetic fixtures (including a perfectly-calibrated and a maximally-overconfident set)
  before touching real rows.
* **C2 — the self-scored cross-check:** on items carrying their own `Expectations N right,
  M wrong` line, the extraction's per-item right/wrong tallies must reproduce the write-up's
  N and M exactly; any mismatch is listed, and more than 2 mismatches → back to stage 0.
* **C3 — no-market-data pin:** the script imports nothing under `valuation/edge/` except
  `power_gate`/`statistics` helpers, opens nothing under `data/` except `free_analysis`, and
  a test asserts both (the AST-pin idiom of `MB15`/`MB16`).
* **C4 — cluster non-vacuity:** the cluster bootstrap must widen the naive CI on the real
  data; if it narrows it, the interval code is wrong (the `MB1` clustering pin, reused).

## 7. Void conditions

1. Reading, joining, or recomputing anything from market data (panel, chains, prices, ticks).
2. Editing any ledger row, log row, or register — this study **reads** the record.
3. Quoting any per-item result as evidence for or against re-opening that item: aggregates
   only. (A calibration study that re-litigates `S19` has become a re-open engine.)
4. Adding a repo-wide check that fires on historical registers (`MB30`/`MA21` bind).
5. Computing Storey π₀ / local FDR over pooled t-stats **in this register** — the archive's
   t-stats are heterogeneous (different bars, books, clustering) and pooling them needs its
   own design; named here so its absence is a decision, not an oversight.
6. Charging any counter other than infra.

## 8. Deliverables

`scripts/sc1_prior_calibration.py` (stage 0 + stage 1/2), the per-pair extraction table
(banked, rule 9), `data/free_analysis/SC1_PRIOR_CALIBRATION.json`, a handoff section, one
RESEARCH_LOG infra row, one out-of-band ledger row (`LOO`/`SELRULE` precedent), and — verdict
permitting — one paragraph proposed for `/research` in `MB38`'s cleared vocabulary (a count,
a gap, a verdict word; never a performance figure; the withhold() kill inherited verbatim).

## 9. Expectations, written before the run, to be scored afterwards

1. ≥ 40 scoreable OUTCOME pairs exist — **70/30**.
2. The primary verdict is OVERCONFIDENT-OPTIMISTIC — **70/30**.
3. Class-(a) shrinkage median lands in [0.3, 0.7] — **60/40**.
4. Halves sign-agreement (stability set) exceeds 70% — **55/45**.
5. Double-entry disagreement is under 8% — **60/40**.
6. At least one number here contradicts an expectation in this list — **60/40**, on the
   record's own base rate.

## 10. What this register does NOT do, named so it is not mistaken for done

It does not open any market data. It does not re-open, re-score, or re-litigate any trial. It
does not compute π₀ (void 5). It does not police historical registers (void 4). It does not
ship a product surface — it *proposes* one paragraph through the existing `MB38` gate. And a
CALIBRATED verdict does not validate any individual prior, exactly as an index fund's return
validates no individual stock pick.
