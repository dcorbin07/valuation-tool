# B13 + S7-4 — RESULTS
## Executes `PREREG_b13_s7d_liquidity.md` unmodified. **2 EQUITY TRIALS. ADOPTS NOTHING.**
## 2026-08-27.

Register committed **ALONE and BLIND** at `3ca48bb` (markdown only), a strict ancestor of the
trial booking at `360b245`, which is itself a strict ancestor of the runner. Equity `N` **243 →
245**; options 310 and infra 20 untouched. **No file under `valuation/` changed**, no constant
moved, no arm adopted.

---

## 1. COVERAGE, STATED BEFORE EITHER ARM RAN

| | |
|---|---|
| panel cells | 113,945 |
| **with a point-in-time ADV** | **90,025 = 79.01%** |
| covered dates (≥20 names) | **64 of 69** |
| halves | **32 early / 31 late**, boundary **2017-01-19 embargoed** |
| CRSP's 2024-12-31 cut costs | **5 dates, 9,367 rows** |
| covered cells below the $500k floor | **1,678 = 1.86%** |

**79.01% IS THE CELL-LEVEL FIGURE AND IT IS THE ONE THAT GOVERNS.** The 89.7% is name-level; a
name can resolve to a permno and still have no usable ADV on a date. Quoting the name-level
number for a cell-level arm is the population mismatch `MB8` and `V6-OPT` both paid for.

`MIN_AVG_DOLLAR_VOLUME = $500,000` was **IMPORTED** from the shipped config, never retyped.
`C1` reproduces the published record exactly, so the harness scores the same object the record
describes.

---

## 2. ARM 1 — `B13`: **PASSES NON-INFERIORITY**, and the loss is real and tiny

| half | base alpha | filtered alpha | **loss** |
|---|---|---|---|
| early (32 dates) | 2.333% | 2.289% | **−0.0431 pp** |
| late (31 dates) | 9.439% | 9.155% | **−0.2837 pp** |

**Margin: 1.8629 pp** (X7's calibrated alpha margin as recalibrated by `MA19`; `MB31` derives
that no placebo floor can move below equity `N` = 247 and this run sits at 245, so it is current).
The losses are **43×** and **6.6×** smaller than the margin.

### THE LOSS IS A LOSS, AND THAT IS THE REGISTERED EXPECTATION, NOT A FAILURE

Both halves lost alpha, exactly as declared in advance. **`B13` is a CREDIBILITY claim, not an
alpha one:** dropping illiquid names removes the part of the cross-section where measured returns
are largest and least tradeable, so a prefilter that *improved* alpha would have been the
surprising outcome and a flag to check the filter binds at all. A backtest holding names nobody
could have bought at size is not wrong about its arithmetic — it is wrong about what it is a
backtest **of**.

### POWER, AT BOTH VOCABULARIES, AND IT IS WHAT MAKES THE PASS WORTH ANYTHING

| | |
|---|---|
| paired periods | 44 |
| paired SE | 0.002051 |
| **MDE at 50% power** (`crit·se`) | **0.4101 pp** |
| **MDE at 80% power** (`(crit+0.84)·se`) | **0.5824 pp** |
| ratio | 1.42× |

`crit` is the **conventional 2.0 and is labelled UNCALIBRATED**: `V2G` established there is no
calibrated floor for a paired within-panel difference, and X7 calibrated *levels* on the decile
book, so borrowing one of its floors here would be the cross-configuration comparison this record
has already paid for twice.

**THE 80%-POWER MDE (0.58 pp) IS 3.2× SMALLER THAN THE MARGIN (1.86 pp), SO THIS NON-INFERIORITY
PASS IS GENUINELY INFORMATIVE RATHER THAN A STATEMENT ABOUT LOW POWER.** `MB8`'s distinction: a
design whose resolution is far finer than its bar can actually assert non-inferiority; one whose
resolution is coarser can only assert "undetectable".

**And the honest other half: both observed losses sit BELOW even the 50%-power MDE, so neither is
separable from zero.** The right sentence is *"the filter costs no alpha this design can resolve,
and the design can resolve effects three times smaller than the margin"* — not *"the filter costs
0.28 pp"*.

### WHAT THE FILTER ACTUALLY BUYS, reported beside the verdict

| | |
|---|---|
| cells removed as illiquid | **1,678 = 1.47% of the panel**, 217 names |
| cells **unmeasured and KEPT** | **23,920** |
| removed names' median market cap | **$275.9 M** |
| kept names' median market cap | **$5,475.9 M** |

**The removed names are 5.0% the size of the kept ones — a 19.9× gap** — which is what a
liquidity floor is supposed to look like. **A filter removing 1.47% buys different credibility
from one removing 40%, and the alpha number alone cannot tell them apart**, which is why both
ship.

**UNMEASURED NAMES WERE KEPT, NEVER FILTERED.** All 23,920 of them. Dropping a name for having no
ADV would make this a data-availability screen wearing a liquidity screen's name — `S10`'s exact
defect — and here it would correlate with era (coverage runs 78.6% → 96.2%), with size and with
delisting.

---

## 3. ARM 2 — `S7`-4 `size × liquidity`: **REJECTED**, on S7's gate, imported

| half | Δ top-decile alpha | Δ long-short *t* | clears? |
|---|---|---|---|
| early (32) | **−0.18 pp** | **−0.358** | no |
| late (31) | **−3.05 pp** | **−0.924** | no |

Gate: **≥ +100 bps alpha AND ≥ +0.25 long-short *t*, in BOTH halves, boundary embargoed** —
`gate`, `evaluate`, `MIN_ALPHA_GAIN`, `MIN_TSTAT_GAIN`, `THEMES` and `W` are **imported from
`scripts/s7_s18_interactions.py`**, so "verbatim" is a fact about the call graph rather than a
claim in prose.

**Negative on both metrics in both halves, so REJECTED rather than NOT_REPLICATED.** The label
`ELIGIBLE — UNREPLICATED, 1 OF 7 SIBLING ARMS` was prepared and **is not used**, because nothing
cleared.

Power: paired SE 0.009268, **MDE 50% = 1.85 pp, MDE 80% = 2.63 pp**. The late half's −3.05 pp
**exceeds** the 80%-power MDE, so that harm is resolvable; the early half's −0.18 pp is well below
it and is not. **So the arm is rejected on a gate it fails decisively in the late half and
inconclusively in the early one, and the rejection rests on the gate's both-halves rule rather
than on two independent measurements.**

**`S7`-4 joins its three siblings: all four of the audit's named interactions are now measured,
and none clears.**

### THE C7 DILUTION CONTROL IS DEGENERATE HERE, AND SAYING SO IS THE POINT

`S7`'s C7 isolates the dilution an eighth input causes by re-scoring with a **constant** eighth
column. Reproduced here it returns **exactly 0.0 in both halves** — and that is **not a pass**.

**In a fixed-weight SUM, adding a constant column shifts every score equally and cannot change a
ranking, so the delta is 0.0 by algebra rather than by measurement.** A control that cannot fail
is not evidence, and reporting "C7 clears" would be the blank-counter family this record keeps
hitting — `MB21`'s C1 scoring a perfect zero on an empty frame, `SC-1b`'s double-entry check
returning a confident 0.0000 against a published 11.7%.

**And it is informative about `S7` rather than about this arm: S7's own C7 measured +0.000173 /
+0.000146, which is NON-zero, so S7's construction cannot have been a pure fixed-weight sum and
its dilution control does not transfer.** The register said to *reproduce* it rather than assume
it carries over; reproducing it is what showed that it does not.

---

## 4. A DEFECT IN MY OWN RUNNER, AND IT PRODUCED A CLEAN FALSE VERDICT

**The panel's `date` column is `str`.** The first run converted the covered-date keys to
`datetime.date`, so `evaluate`'s `isin` matched **zero rows** — and the output was not an error.
It was **`ARM 1: INSUFFICIENT` and `ARM 2: REJECTED`**.

**That second one is the dangerous half: a rejection reached by comparing nothing is
indistinguishable from a real one**, and `S7`-4's true verdict happens to *be* REJECTED, so the
wrong answer and the right answer wore the same word. `MB21`'s C1 defect in a new place.

Repaired by keeping the keys as strings, and pinned by `_require_scored`, which **refuses to
report any verdict whose splits scored no dates**. The gate is on the COUNT, not the values —
`MB21`'s own lesson.

---

## 5. WHAT THIS DOES NOT SAY

* **Nothing is adopted.** `MIN_AVG_DOLLAR_VOLUME` is still unwired on the panel path,
  `prefilter_adv_wired` still reads `false`, no interaction column ships, and no published figure
  moves. Wiring the prefilter is a construction change and a **vintage event**, and it is Don's.
* **Neither arm says anything about 2025 or 2026.** CRSP is cut at 2024-12-31 and both arms run
  on 64 of 69 dates.
* **`B13` passing non-inferiority is not evidence the book is liquid** — it is evidence that
  *applying the shipped floor costs no alpha this design can resolve*. Only 1.86% of covered
  cells sit below the floor, so the filter barely binds on this universe, and a floor that
  removes 1.47% of the panel cannot certify the other 98.5%.
* **The 79.01% coverage means ~21% of cells carry no measure at all**, and those were kept. `B13`
  therefore still cannot bind *universally* — which was its original claim and remains true.

**EXPECTATIONS: 5 right, 0 wrong** (the sixth was declared unscored). B13 passes non-inferiority
(70/30) ✓; the alpha change is a real LOSS (80/20) ✓ in both halves; the floor removes under 15%
of covered cells — **1.86%** (60/40) ✓; `S7`-4 is REJECTED (75/25) ✓; removed names' median market
cap is under a fifth of kept — **5.0%** (70/30) ✓. **A clean sweep is worth discounting, not
celebrating:** four of the five follow from the panel being a large-cap universe and from this
project's standing null, and the register was written by the same person who ran it.

`scripts/b13_s7d_arms.py`; `data/free_analysis/B13_S7D_ARMS.json`.
