# PRE-REGISTRATION — U3: a convex overlay on the equity book, sized as insurance

**Committed before any scorer exists.** One `.md`, zero `.py`. Frozen books on both sides: the
split-clean options book (`state_r2_splitclean.pkl`, 3,870 trades) and the corrected 69-date
equity panel (`panel_corrected_69d.pkl`). No re-mine, no panel rebuild, no live code path
changed, and **nothing here can adopt anything** — an eligible result is recorded ELIGIBLE and
routed to Don, because the options sleeve's weight is a capital-allocation decision.

Companion design memos for `U4`, `U6` and `U8` are filed separately as `DESIGN_u4_u6_u8.md`.
They register no hypothesis and charge no trial.

---

## 0. Premise findings — measured BEFORE this register was written

Each of these changed the design. They are stated first so that nothing below reads as a choice
made after seeing a result.

### 0.1 The ledger is wrong about two of these four rows, in the same way it was wrong six times in the O-series

`VALQUO_LEDGER.md` carries `U3` and `U8` as `src=auto` with the note *"no mention anywhere in
the corpus"*. **Both are false.** `VALQUO_EDGE_AUDIT.md:1268` is a full `U3` section with a
four-step method, a named measurement trap and a pre-registered threshold; `:2123` is a full
`U8` section. That is now **eight** `src=auto` rows in this lane found to assert absence where a
full audit section exists. The definitions below are **quoted from the audit, not invented**, and
all four ledger rows are corrected as part of this item.

`U4` (`:1290`) and `U6` (`:2091`) are `src=human` and both notes are accurate.

### 0.2 THE SLEEVE IS NOT A LONG-VOLATILITY SLEEVE. IT IS 100% LONG CALLS AT +0.37 DELTA

The audit's reframe is that *"Valquo has already built [a long-volatility sleeve] by accident"*
and that a long-vol profile is *"valuable as portfolio insurance, because [it pays] when
everything else does not."*

Measured on the frozen book: `opt_right` is **`call` on 3,870 of 3,870 rows**, `horizon` is
**`swing` on 3,870 of 3,870**, and mean `target_delta` is **+0.3725** (median +0.3575). There is
no put, no short leg, no straddle. **A long call is long vega AND long delta**, and for a large
adverse move in the underlying the delta leg dominates the vega leg.

So the audit's premise is a hypothesis about this book, not a description of it, and **it is
testable directly**. This is the U7/S10 failure mode — an instrument wearing a name that
describes a different instrument — and it is the reason the mechanism arm (A2 below) exists
rather than being assumed away.

### 0.3 COVERAGE: 40 OF 69 QUARTERS, AND EVERY UNCOVERED ONE IS EARLY

Options alerts span **2016-01-19 → 2025-10-15**; the equity panel spans **2009-01-15 →
2026-01-28** over 69 rebalance dates. **40 of 69 equity quarters carry ≥5 sleeve trades**
(2016-01-20 → 2025-10-27) and **all 29 uncovered quarters are early**. This is S18's and U2's
situation for the third time: a both-halves gate on the *full* panel is **impossible**, not
merely weak. Every split below is of the **covered subsample**, 40 dates, and the halves are
20 and 19 after embargoing the boundary — both above the shipped `min_dates=16`.

**A pass on 20-date halves is not the same object as a pass on 34-date halves**, and no figure
here may be compared with a full-panel one.

### 0.4 THE SAMPLE CONTAINS ONE CRASH, AND THE AUDIT ITSELF SAYS THAT MAKES THE OBVIOUS TEST DOOMED

`S10` measured that this book's worst peak-to-trough spans **exactly one 63-day period on every
arm, at the same trough index 44 of 69** — COVID 2020Q1. The covered subsample contains that
episode and no other of comparable size.

`VALQUO_EDGE_AUDIT.md:1549`, writing about the sibling regime overlay, states the consequence
in its own words: *"A crash-insurance rule cannot clear a both-halves gate unless the sample
contains two comparable crashes. The panel has one. Structuring the test this way guarantees
rejection regardless of the rule's merit."* It adds at `:1553` that recording such a result as a
failed test, when it is an **untestable hypothesis under the chosen protocol**, is the error to
avoid *"so nobody re-runs the same doomed test."*

**That warning binds this item, and §4.3 below is written to honour it rather than to trip over
it.** The verdict rule is deliberately **asymmetric**: this design can return a decisive REJECT
without a second crash, and it **cannot** return a decisive ADOPT.

### 0.5 DISCLOSURE: THIS REGISTER IS NOT BLIND ON THE SIGN OF THE MECHANISM ARM

A crude probe was run before this register, to decide whether U3 was measurable at all. It
computed an unweighted attribution — the mean per-trade mark-to-mark change inside each equity
rebalance window, with **no capital constraint, no concurrency cap, no costs and no portfolio
construction** — and reported a correlation of **+0.5418** between that series and the equity
top-decile return over the 40 covered quarters, with a mean sleeve return of **−53.50%** in the
worst decile of quarters against **+15.92%** across all covered quarters.

**I am therefore not blind to the SIGN of arm A2, and this register does not claim to be.**
Three things make it worth writing anyway, and they are stated so a reader can discount rather
than trust:

1. **The adoption bar is the audit's own, quoted verbatim** — *"Adopt only if the combined
   Sharpe improves and maximum drawdown falls"* (`:1284`). It was fixed by someone else, before
   I looked at anything, and I cannot tune it to a result.
2. **The probe did not compute the primary statistic.** A1 is combined Sharpe and maximum
   drawdown of a capital-constrained, costed combined book swept over X = 90…99. The probe
   computed none of those quantities, and an attribution mean is not a portfolio return.
3. **The probe's construction is not the instrument's** and its numbers are expected to move.
   Only the sign of A2 is carried over.

What remains genuinely unmeasured: every A1 cell, the costed drag, the conditional correlation
under the **implied-vol** split the audit demands (§2.4), and whether any X in the swept range
satisfies the audit's conjunction.

---

## 1. Scope — what this tests, and what it does not

**Tested.** Whether adding the existing single-leg options book to the existing equity book, at a
small capital weight, improves the combined book's Sharpe **and** reduces its maximum drawdown —
the audit's U3 method at `:1276-1284`, run on the covered subsample.

**NOT tested, and named so it is not later mistaken for tested:**

* **Any options book other than the one that exists.** The audit's insurance argument is really
  an argument for a long-vol sleeve. A *put* sleeve, a straddle sleeve, or an index-hedge sleeve
  would each be a different instrument and a new register. This item tests the book the project
  actually has, which §0.2 measures to be long calls.
* **Whether a convex overlay is a good idea in general.** A null here is a statement about this
  sleeve on this sample, not about portfolio insurance.
* **Re-optimising the equity book.** It is held exactly fixed at the deployed flat 1/7
  seven-theme composite, top decile, the configuration every published figure uses.

---

## 2. Definitions — fixed here, before any scorer exists

### 2.1 The equity leg
The shipped `quantile_backtest` on `panel_corrected_69d.pkl` with the deployed weights, `n_q=10`,
`horizon=63`. The per-period top-decile return is **`alpha[i] + equal_weight[i]`**, which is an
identity in the shipped code (`fundamental_panel.py:2612-2615`: `ewb` is `mean(fwd)` and
`alpha_series` is `mean(fwd[top]) − mean(fwd)`). `equal_weight` is not currently exposed;
adding it to the opt-in `series` dict is the **only** production change this item makes, it is
inside the existing `return_series` gate, and **every existing caller's payload stays
bit-identical** (V2G's own precedent). A test pins the identity.

### 2.2 The sleeve leg
A capital-constrained mark-to-market curve built from `O11_MARKS.pkl` (161,610 daily marks over
3,870 contracts, spanning 2016-01-19 → 2025-12-19), **not** from per-trade P&L attributed to exit
dates — a lumpy exit-date attribution would put the crash quarter's losses in the wrong quarter.
Sizing follows **O11's measured result**, not a fresh optimisation: flat notional per trade with
a **concurrency cap**, and O11's own finding that the cap binds hardest in the crowded weeks is
inherited as a property, not re-derived.

### 2.3 Costs
The **measured** stack, not an assumption: entry and exit each pay **ρ = 0.6743** of the quoted
half-spread (O18's measured effective-to-quoted ratio, CI95 [0.6617, 0.6871]), applied to each
contract's own `entry_spread_pct`. The `$0.0545` availability term O18 measured is **NOT**
credited as a saving — O18 established it is selected, not an execution property.

### 2.4 The conditional correlation, and the trap the audit names
Arm A2 splits quarters on **ATM implied volatility**, never on realised return. The audit
records at `:1282` that the VRP work's return-based split gave 0.233 vs 0.335 and was correctly
identified as a **conditioning artefact**, and that an implied-vol split moved the same quantity
from 0.254 to 0.610. A return-based split here would select quarters on the very variable being
correlated. **The IV split is the primary; a return-based split is reported only as the
demonstration of the artefact.**

### 2.5 Halves
The 40 covered quarters, split at the median date, boundary embargoed: 20 early and 19 late.

---

## 3. Bars — and every one of them is UNCALIBRATED

**The audit's own threshold, verbatim (`:1284`):** *"Adopt only if the combined Sharpe improves
and maximum drawdown falls. A long-vol sleeve that improves Sharpe by raising return is not
doing the job it is being hired for."*

**X7 CALIBRATES NO FLOOR FOR SHARPE, FOR MAXIMUM DRAWDOWN, OR FOR A CORRELATION.** S13 recorded
this for Sharpe and drawdown; S10 recorded it again for drawdown and labelled its 2.0pp bar
uncalibrated for exactly this reason. **So every bar in this item is a convention, and is
labelled so wherever it appears.** No figure here may be compared with 2.71, 2.2837 or 2.2913,
which are calibrated for different statistics on a different object.

Three further rules fixed now:

* **`max_drawdown` is NEGATIVE**, so an arm improves it by being **less** negative and the gain
  is `arm − base`. S10's first cut computed `base − arm` and reported a 2.61pp worsening as a
  2.61pp improvement. A test carries the real measured pair.
* **Both legs of the conjunction must hold in BOTH halves** for eligibility.
* **A miss is a miss.** Ambiguous against a pre-committed threshold is a NULL (`RUN_RULES` A6).

---

## 4. Arms and verdict rules

### A1 — THE OVERLAY (the verdict arm)
Combined book at **X ∈ {90, 91, …, 99}** percent equity, sleeve at (100−X), rebalanced at each
equity rebalance date, costed per §2.3. Report combined annualised return, Sharpe, maximum
drawdown and turnover at every X, **and report the whole curve** — no cell is selected after the
fact. **ELIGIBLE** only if some X improves Sharpe **and** improves maximum drawdown, in **both**
halves. Otherwise **REJECTED**.

### A2 — THE MECHANISM (does the sleeve pay when the equity book does not?)
Correlation of the sleeve's quarterly return with the equity book's, and the sleeve's mean return
conditioned on the equity book's worst decile of quarters, under the §2.4 IV split.
**Pre-committed reading, and §0.5 discloses that I have seen a crude version of its sign:** a
positive conditional correlation means the sleeve is **not insurance**, and no capital weight can
make it insurance — which is a decisive REJECT of A1's premise that does **not** require a second
crash.

### A3 — THE COST OF CARRY (measurement, no bar, charges no trial)
The sleeve's annualised drag on the combined book at each X, decomposed into the sleeve's own
expectancy and the measured spread cost. Reported so that "the insurance costs less than what it
insures" is answerable in dollars rather than in Sharpe units.

### 4.3 THE ASYMMETRY, FIXED IN ADVANCE PER §0.4

* **A decisive REJECT is available from this sample.** If A2 shows the sleeve co-moves *with* the
  equity book, the failure is one of **sign**, which is measurable in all 40 quarters and does not
  depend on the crash count.
* **A decisive ADOPT is NOT available from this sample.** If A1 were to clear, the drawdown leg
  would rest substantially on **one episode**, and per `:1549` that is an untestable hypothesis
  under this protocol. **Such a result must be reported `ELIGIBLE-BUT-UNRESOLVED`, never
  `ADOPTED`, and its drawdown improvement must be quoted with the number of distinct drawdown
  episodes supporting it.**
* **A REJECT is therefore worth more than a pass here, and that is a property of the sample, not
  of the strategy.** Nobody may read a rejection as evidence that portfolio insurance does not
  work.

---

## 5. Controls

* **C1 — harness.** The equity leg must reproduce the published record (top-decile alpha
  +7.1741%, long-short naive *t* 2.8361, HAC 2.6199, monotonicity −0.8909, equal-weight
  +18.1371%). The run **ABORTS before any arm is read** if it does not.
* **C2 — the sleeve reproduces its own record.** The banked book's mean per-trade P&L must come
  back at **+3.2702%** on 3,870 trades before any curve is built.
* **C3 — no look-ahead in the join.** A sleeve mark may only enter quarter *q* if its date lies
  in [start(q), start(q+1)). Zero violations required.
* **C4 — the identity of §2.1.** `alpha + equal_weight` must equal the directly computed
  top-decile return to floating-point tolerance on every date.
* **C5 — the cost stack is not free money.** Setting ρ = 1.0 (pay the full quoted half-spread)
  must make every A1 cell weakly worse. A cost model that improves an arm is a bug.
* **C6 — the artefact the audit names.** Report the conditional correlation under BOTH the IV
  split and the return split, and state which is primary (§2.4). If they disagree in the
  direction the audit predicts, that is a reproduction of its warning, not a finding of this item.
* **C7 — the sleeve is not a market proxy.** Report the sleeve's correlation with the
  equal-weighted universe as well as with the top decile. If the two are indistinguishable, the
  sleeve carries no book-specific information and A2's reading is about beta, not about the book.
* **C8 — degenerate X.** At X = 100 the combined book must equal the equity book exactly
  (max |Δ| < 1e-12) on every reported field. A sweep whose endpoint does not reproduce its own
  baseline is measuring something else.

---

## 6. Expectations, written down first

Recorded because this project's directional calls keep being wrong and writing them down is the
only thing that keeps that visible. §0.5 means expectation 1 is **not a prediction** and is
excluded from the score.

1. *(EXCLUDED — sign already seen)* A2's conditional correlation is positive; the sleeve is not
   insurance.
2. **80/20** — no X in 90…99 clears the audit's conjunction in both halves.
3. **70/30** — the sleeve's drag is larger than any drawdown benefit it buys at every X.
4. **65/35** — the return split understates the conditional correlation relative to the IV split,
   reproducing the audit's named artefact.
5. **60/40** — the sleeve's correlation with the equal-weighted universe is within 0.10 of its
   correlation with the top decile (C7), i.e. it is mostly beta.
6. **55/45** — maximum drawdown of the combined book is *worse* than the equity book alone at
   every X, not merely no better.
7. **75/25** — the crash quarter (2020Q1) is the single worst quarter for the sleeve as well as
   for the equity book.

## 7. Trial cost

**Two options trials**, charged whether or not a verdict issues (session 26's rule: running and
then voiding does not refund the search):

* A1 — the overlay, one pre-specified sweep reported whole (S14's precedent: a pre-specified grid
  reported in full is one trial, not ten).
* A2 — the mechanism arm, which carries its own pre-committed reading.

A3 charges nothing: it has no bar and returns no verdict. The three design memos charge nothing
(session 8 and S25's precedent — a fact about what data exists is not a hypothesis).

**Domain: options.** The equity book is held fixed and the object searched over is the options
sleeve and its weight, so it pays options rent. The `unified` domain is deliberately not used:
it stands at N = 0 and **no calibrated bar exists for it**, so charging there would invent a
denominator that gates nothing.

## 8. Void conditions

The run returns **NO VERDICT** if any of these fires:

1. C1 or C2 fails — the harness does not reproduce the record on either side.
2. C3 finds any look-ahead cell.
3. C8 fails — X = 100 does not reproduce the equity book.
4. Fewer than 16 covered quarters land in either half.
5. The sleeve curve is built from anything other than `O11_MARKS.pkl` and the frozen split-clean
   book.
6. Any bar in §3 is moved after a number is read, or any figure is compared with a calibrated
   equity floor.
7. The X grid is extended, refined, or a cell is selected post hoc.
8. A favourable A1 result is reported as `ADOPTED` rather than `ELIGIBLE-BUT-UNRESOLVED` (§4.3).
9. A cost assumption is substituted for O18's measured ρ after a result is seen.
