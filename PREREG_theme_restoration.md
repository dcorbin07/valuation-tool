# PRE-REGISTRATION — THEME RESTORATION: the fidelity gate before any wiring

**Committed alone, before any wiring or any fidelity number exists.** No measurement code for
this task has been written at the time of this commit.

The case for restoring is COHERENCE, not performance: the live book scores **4 of 7** weighted
themes and **fails the calibrated long-short floor (1.8811 vs 2.2837)**, while the validated
seven-theme composite clears it (2.6199). Live must run what was validated. This document is the
gate that decides *whether it can be*, per theme, before a line of scoring code changes.

---

## 1 · THE DANGER THIS GATE EXISTS TO PREVENT

My live sources are **approximations**. The panel's themes come from licensed Sharadar SF2/SF3;
mine come from raw EDGAR — 13F structured data sets, XBRL company facts, and the Form 4 scraper.
They are different instruments measuring the same intent.

**Wiring a DIFFERENT theme under a validated theme's name is the B7 disease** — the live product
computing a different composite from the one every published figure is measured on. Restoring an
unfaithful column would not fix the coherence problem; it would *hide* it, by making the live
book look seven-theme while scoring something the backtest never validated.

**Skipping a theme stays strictly better than faking it.** A four-theme book that says it is a
four-theme book is honest. A seven-theme book with one impostor column is not.

---

## 2 · THE FIDELITY TEST

**Statistic:** per theme, the **Spearman rank correlation** between my live theme value and the
panel's own theme value, over tickers present in both. Spearman because both sides are
standardised differently (mine within the 500-name served universe, the panel's within its own
cross-section) and rank correlation is invariant to any monotone rescaling — so the test measures
*does this rank names the same way*, which is the only question that matters for a composite built
by ranking.

**Cross-section:** the panel's **most recent** rebalance date. Live values are a single snapshot,
so this is the closest available alignment.

### 2.1 THE BAR, FIXED NOW

    FIDELITY_BAR = max(0.60, P95 of |Spearman| between DIFFERENT panel themes
                                on the same cross-section)

Two components, both stated before measuring:

* **0.60 floor** — an absolute floor. Below this, most of the rank information differs and
  calling it "the same theme" is not defensible whatever the calibration says.
* **The calibrated component** — a live theme must agree with its panel counterpart **better than
  distinct panel themes agree with each other.** If `live institutional` correlates with
  `panel institutional` no better than `panel momentum` does, then it is statistically
  indistinguishable from *a different theme*, which is precisely the failure being guarded
  against. This is the X7 method — score a statistic against what the same data produces when the
  relationship is not the one claimed — applied to a correlation instead of a *t*.

The calibrated component is computed **from the panel alone**, needs no live data, and is
therefore not informed by any fidelity result.

### 2.2 SUPPORTING CONDITIONS

* **`n ≥ 100`** overlapping non-null pairs. Below that the estimate is too thin to carry an
  adoption; the theme is recorded **NOT MEASURABLE** — neither pass nor fail — and does not
  restore.
* **Direction:** ρ > 0 with p < 0.01. A negative or insignificant correlation fails regardless of
  magnitude.
* **Reported but NOT binding:** quintile agreement (fraction of names landing in the same quintile
  on both sides). Diagnostic colour; it decides nothing.

### 2.3 THE CONFOUND, STATED BEFORE MEASURING, BECAUSE IT DECIDES HOW A FAILURE READS

The panel's last cross-section and my live snapshot are **not the same date**. That gap is not
removable here: the panel ends where the licensed export ends, and my live values are current.

**This makes the test CONSERVATIVE FOR A PASS and AMBIGUOUS FOR A FAIL.** A theme that clears the
bar across a time gap is faithful *and* stable — a strong result. A theme that fails cannot be
attributed to the source, because source disagreement and genuine drift over the gap are not
separable by this design.

Per theme, committed now:

| theme | how aligned are the two windows | how a failure must be read |
|---|---|---|
| `capital_discipline` | **good** — annual share issuance, slow-moving, and the cached XBRL values end in **2025-10-31**, i.e. *before* the panel's last date | a failure is mostly attributable to the SOURCE |
| `institutional` | **adjacent** — my 13F periods vs the panel's most recent public quarter; holder breadth moves slowly | mostly SOURCE, with some drift |
| `insider` | **DISJOINT** — my Form 4 window is the last 90 days; the panel's is its own, ~6 months earlier. Insider activity is bursty and does not persist | **a failure CANNOT be attributed to the source.** It must be recorded as NOT DEMONSTRATED, with the fix named, not as "the source is bad" |

---

## 3 · COVERAGE FLOORS — the standing rule, unchanged

A theme that passes fidelity must also clear the project's existing constants, applied to the
500-row served universe: `COVERAGE_FLOOR = 0.05`, `MIN_COVERAGE = 0.30`, `MIN_DISTINCT = 2`.
A constant column is **not** covered however full it is — `zscore` returns all-NaN on it and
`composite` renormalises it away, which is the state `insider` is in today.

---

## 4 · RESTORATION, AND THE VINTAGE ARITHMETIC

**Restoration = the passing themes enter `composite_score` at their DEPLOYED weights** (0.125
each, per vintage 2's pinned snapshot). Nothing is retuned. A theme that fails does not enter.

### 4.1 A CORRECTION TO THE BRIEF'S NUMBERING, because it changes what gets recorded

The brief says *"vintage 2 opens"* and *"vintage 1's four-theme composite runs in shadow"*. Both
are off by one against the record and the code:

* `CLAUDE.md` and `shadow_vintage.PINNED` show **vintage 2 has been open since 2026-08-10**, its
  parameters already pinned (`params_id 0060c5ef3dda`).
* `shadow_vintage.py:114` states the successor case explicitly: *"When an adoption opens
  **vintage 3**, its predecessor's parameters are already here"*, and `open_pairs()` is documented
  as *"Empty until an adoption opens vintage 3."*

**So: adopting CLOSES vintage 2 and OPENS VINTAGE 3, and the book that runs in shadow is
VINTAGE 2's** — the four-theme composite actually in production today. Registered with the
corrected numbering; recording it under the brief's numbers would put a wrong vintage id in a
register whose whole value is being citable years later.

### 4.2 IS THIS EVEN A VINTAGE EVENT? THE ARGUMENT AGAINST, AND WHY IT LOSES

There is a real argument that it is not. **Vintage 2's pinned snapshot already declares all seven
themes at 0.125** — live simply never delivered three of them. On that reading, restoration is a
*bug fix* bringing live into conformance with the vintage it already declared, and no clock
resets.

**That argument loses, and the reason is the forward track.** Amendment 1 defines "adopted" as
*ships in the live scoring path*, and the composite users receive **will change materially** —
42.9% of the weight mass starts contributing. Whatever the paper track has accrued since
inception, it accrued while recording a **four-theme book**; that record describes the four-theme
book and cannot be carried forward as evidence about a seven-theme one. **Rule 6 applies in full:
the accrued clock resets and buys nothing statistically.**

Recorded here because it is exactly the argument someone will reach for later to avoid paying the
reset, and the answer should be on the record before anyone needs it.

### 4.3 IF NOTHING PASSES

**No theme passing fidelity means NO adoption, NO vintage event, and vintage 2 stays open.** The
live book remains a four-theme book and the record says so. That is a legitimate outcome of this
gate, not a failure of it.

---

## 5 · WHAT A FAILURE MUST CARRY

Any theme failing fidelity, coverage, or measurability is recorded with **exactly what would fix
it** — a better source, a longer history, or a date-aligned rebuild — stated concretely enough
that the next person can act on it without re-deriving the diagnosis.

---

## 6 · EXPECTATION, WRITTEN DOWN FIRST

* **`capital_discipline` passes — 60/40.** Share issuance is a mechanical quantity both sources
  compute from the same filings; if anything is faithful, it is this.
* **`institutional` passes — 50/50.** A genuine coin flip: SF3 is an aggregation with its own
  cleaning, and my join is a two-rung CUSIP ladder with a 82.2% hit rate.
* **`insider` fails or is not measurable — 75/25.** Disjoint windows, and the live column is
  35.8% pinned at exactly 50.0.
* **Overall: I expect ONE or TWO themes to restore, not three — 70/30.**

*(This project's directional calls have been wrong more often than right. The point of writing
them down is that they keep being wrong.)*

---

## 7 · WHAT VOIDS THIS RUN

* Any threshold in §2 or §3 edited after this commit.
* The fidelity comparison run on anything other than the panel's own theme columns.
* Restoration of a theme that did not clear both fidelity and coverage.
* A vintage opened without its predecessor's parameters already pinned.

## 8 · TRIAL COST

**Zero. Equity `N` does not move.** This searches nothing: it applies a fixed, pre-stated bar to
three fixed columns and either wires them or does not. No parameter is chosen, no arm is selected,
and the deployed weights are the ones already in the pinned snapshot. A vintage event is charged
against the forward clock (Rule 6), which is a different and much more expensive currency than
`N`, and §4.2 states that price explicitly.
