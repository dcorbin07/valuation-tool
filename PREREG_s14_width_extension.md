# PRE-REGISTRATION — `S14-WIDTH`: extend the no-trade-band width grid past 0.30

**Written and committed BEFORE any measurement at a width above 0.30 exists.** This file is
committed **alone** — one `.md`, zero `.py` — and is a **strict git ancestor** of every commit
that produces a number for it. Nothing in it may be edited after a result is read; corrections
go in the write-up, against this register, as they did in session 35.

**Date:** 2026-08-13. **Lane:** edge. **Item:** `S14-WIDTH`, the follow-up session 35 named for
itself. **Equity `N` 185 → 186** (one trial; see §8).

---

## 1. Why this exists, and what session 35 actually established

Session 35 ran `S14` — a no-trade band decided on **net** alpha — and it **cleared the held-out
gate in both directions**, the first arm to clear anything in eight sessions. Both directions
picked width **0.30**, net alpha **+1.78pp / +1.77pp**, and turnover roughly **halved**.

**The verdict was recorded ELIGIBLE and explicitly NOT adopted, for one reason: `0.30` is the
widest width the shipped grid contains, and it won both times.** The argmax sat on the boundary,
so the optimum is at or beyond the edge and **the knee was not identified**. The selected width
was an artefact of where the grid stopped, and session 35 recorded in its own §7 and §9 that
widening the grid "is a new measurement needing its own register and is the recommended next
step". This is that register.

**Two corrections session 35 made against its own register travel into this one and change what
is being tested:**

1. **The "pure cost mechanism, no signal claim" framing was WRONG.** Gross alpha *improved*
   (+1.02pp / +0.77pp), so roughly **half** the measured gain is a **signal** effect — holding a
   name until it leaves the top 30% rather than the top 10% stops the book churning on rank
   noise. **This arm therefore makes a signal claim and gets signal-grade scepticism.** It is
   *not* the mechanical cost saving the original framing described.
2. **The measured cost saving is 76–100 bps**, not the ~26 bps computed before the run from the
   audit's quoted turnover. The tightened guard (§3.2) is retained anyway, but the pre-run
   arithmetic that justified it was wrong by ~3×.

---

## 2. The structural fact that bounds this experiment — established from the CODE, before any run

`_band_select` (`fundamental_panel.py:3407`) holds book **SIZE** fixed at `n_target` at every
width. Survivors are kept best-first and the remaining slots go to the highest-ranked names not
held. Two consequences, both verified by reading and exercising the function, **not** by measuring
any return:

* **At `exit_rank == n_target` the band reduces exactly to plain top-N**, which is what makes the
  no-band case a true baseline rather than a different code path (the function's own docstring
  says so; C3 pins it).
* **At `exit_rank == the size of the universe` the book FREEZES.** Every incumbent survives, so
  `keep` is the incumbent set, and the book never changes again except when a name leaves the
  universe entirely. Exercised directly on a synthetic 20-name universe with a 4-name book: the
  same four names are held on all six rebalances.

**This bounds what this experiment can conclude.** The width axis has a **known-degenerate
endpoint**: `exit_frac = 1.0` is buy-and-hold of the first cross-section's top decile for
eighteen years, which no reading of the record supports. **So a true interior optimum must exist
somewhere in `(enter_frac, 1.0)`.** The live question is only whether it lies inside the extended
grid or beyond 0.75 — never whether it exists.

**This is why outcome (b) in §4 is "record and stop" rather than "extend again".** The effect
being unbounded on a grid that stops at 0.75 would say the optimum is somewhere in `(0.75, 1.0)`,
a region where the construction is approaching a frozen book — which is a finding about the
measure, not a licence to keep walking the grid outward until something wins.

---

## 3. The design — identical to `S14`'s, with the grid as the only change

### 3.1 What is swept

The extended grid is the **shipped five plus three conventional round extensions**:

| | widths |
|---|---|
| shipped (session 35) | 0.12, 0.15, 0.20, 0.25, 0.30 |
| **added here** | **0.40, 0.50, 0.75** |

**Round numbers, coarsening as they widen, chosen for being unremarkable.** **No finer spacing is
added anywhere**, including around 0.30 — refining near the incumbent winner is how a grid search
manufactures a knee. `enter_frac` stays at the shipped **0.10** and is **not swept**; nothing else
about the construction moves. `exit_frac` is a fraction of the **universe** (~1,650 names/date),
so 0.75 means a name is sold only once it falls into the bottom quarter of the whole cross-section.

### 3.2 The procedure, verbatim

The same code path as session 35 (`turnover_and_costs`, `top_frac=0.10`, `horizon=63`, deployed
flat 1/7 themes, the shipped cost table):

1. Sweep **every** width in the extended grid on the **DECIDE** half.
2. Take the **argmax of NET alpha** over the widths only — the no-band incumbent is the
   comparator, never a candidate.
3. Measure **that width alone** on the **HELD-OUT** half against the no-band baseline.
4. Repeat with the halves exchanged. Boundary embargoed, as shipped.

**The guard is unchanged and was fixed before session 35's result: an arm improves iff net alpha
improves AND the gross alpha given up does not exceed the MEASURED cost saving.** Because gross
alpha in fact *rose* at 0.30, this guard was slack there; at wider widths it is the binding
constraint and is expected to bite. The audit's own 1.5pp gross allowance is **reported beside**
ours, never substituted for it.

### 3.3 What is reported regardless of the verdict

**The full eight-point net-alpha surface on BOTH halves**, plus gross alpha, turnover and measured
cost drag at every width. **The shape is the deliverable even when the verdict branch is
negative** — a documented surface is what lets the next session see the knee without re-running
anything, and session 35's inability to say where the optimum sat is the entire reason this
register exists.

---

## 4. The three outcomes, committed in advance

Taken verbatim from the instruction that commissioned this run and fixed here before any number:

* **(a) INTERIOR optimum in both directions** — both directions pick a width strictly inside the
  grid (i.e. **not 0.75**), and both clear the guard → **`S14` becomes an ADOPTION DECISION**:
  the knee is identified, and the width plus its measured effect is **routed to Don as a vintage
  event**. It is still not adopted by me.
* **(b) The argmax is still at the new boundary (0.75)** in one or both directions → **the effect
  is real but UNBOUNDED ON THIS GRID. Record it and STOP.** A third extension would be chasing
  the edge, and §2 explains why the region beyond 0.75 is degenerate anyway.
* **(c) The directions disagree** — different widths picked *and* the guard verdicts differ, or
  one direction fails the guard → **NULL**, per the standing both-halves rule (`RUN_RULES` A6).

**Ambiguity resolves to the more conservative branch.** If both directions pick an interior width
but only one clears the guard, that is **(c) NULL**, not (a). If one direction picks 0.75 and the
other picks an interior width and both clear, that is **(b)** — the boundary reading dominates,
because the interior pick cannot identify a knee the other direction contradicts.

---

## 5. Expectations, stated before running

Written down because this project's directional calls keep being wrong, and session 35's were its
worst yet (4 right, 3 wrong, **both consequential misses on S14 itself** — it was predicted to
fail at 70/30 and cleared).

| # | expectation | confidence |
|---|---|---|
| E1 | **The optimum is INTERIOR to the extended grid** — outcome (a) or a near miss, rather than 0.75 winning again | 60/40 |
| E2 | If interior, the picked width is **0.40 or 0.50** rather than something finer | 70/30 |
| E3 | **Net alpha keeps rising from 0.30 to 0.40** in at least one half | 65/35 |
| E4 | **Gross alpha peaks and turns DOWN before net alpha does**, because the cost saving is bounded (§6) while staleness is not | 70/30 |
| E5 | **The two directions pick DIFFERENT widths** — more candidates means more room to diverge, and session 35's agreement on 0.30 was partly an artefact of 0.30 being the only boundary available | 55/45 |
| E6 | **The surface is non-monotone on the late half**, as C6 found at the shipped grid | 75/25 |
| E7 | **The verdict is NOT (a)** — i.e. this does not end as a clean adoption decision | 55/45 |

**E1 and E7 are deliberately in tension** and that is honest rather than sloppy: I expect the
optimum to be interior (E1) *and* I expect the two directions to have a good chance of disagreeing
about it (E5), which routes to NULL (E7). A knee can exist and still not replicate.

**The reasoning behind E4, which is the mechanism claim:** the cost drag at no-band was 0.0227 /
0.0182 and had already fallen to 0.0126 / 0.0106 at width 0.30, so **at most a further ~1.1–1.3pp
of saving is available even if turnover fell to literally zero.** Gross alpha, by contrast, has no
floor — a book drifting toward frozen must eventually give up the entire selection edge (§2).
So net alpha should turn over once staleness costs more than the shrinking remaining saving.

---

## 6. Controls, fixed here

* **C1 — HARNESS.** The run reproduces the published record before any arm is read
  (`top_decile_alpha` 0.07174142332098163, `long_short_tstat` 2.8360640685320595, HAC
  2.6199121240414884, monotonicity −0.8909090909090909). **The run ABORTS before reading any
  width if it does not.**
* **C2 — NOT INERT.** The three new widths must actually change the book. Report annual turnover
  at every width; **if turnover at 0.40/0.50/0.75 is not strictly below 0.30's, the wider widths
  are not doing what their name says** and the arm is void, not merely negative.
* **C3 — THE BASELINE IS THE SAME CODE PATH.** Pin that `_band_select` with
  `exit_rank == n_target` returns exactly plain top-N, so "no band" is a width and not a
  different function.
* **C4 — BOOK SIZE IS CONSTANT ACROSS WIDTHS.** Report the realised book size at every width. If
  it moves, the widths are not like-for-like and every comparison is confounded by book size —
  S23's dilution mechanism in a new costume.
* **C5 — THE DEGENERATE ENDPOINT IS MEASURED, NOT ASSUMED.** Report, at every width, the fraction
  of the book that is a **surviving incumbent** rather than a fresh entry. This is the direct
  mechanical read of §2's freezing argument on the real panel, and it is what distinguishes "the
  band is working" from "the book has stopped selecting".
* **C6 — MONOTONICITY.** Report whether the net-alpha surface is monotone on each half, as session
  35 did. A non-monotone surface is a warning that an argmax is noise, and it is reported whether
  or not it is convenient.
* **C7 — NO RE-USE OF THE MEASURE HALF.** The argmax is taken on the decide half only. Pinned by
  a test that fails if the selection ever reads the measure half.

---

## 7. Void conditions

1. **Adding a width to the grid after seeing any result**, in either direction, for any reason.
   The grid in §3.1 is final. If the surface suggests an optimum at 0.35, that is a finding to
   report, **not** a width to add.
2. **Refining the grid near the winner.**
3. **Sweeping `enter_frac`,** or changing `top_frac`, the horizon, the weights or the cost table.
4. **Switching which metric the argmax reads.** It is NET alpha, as in session 35. Swapping to
   gross, or to a *t*-statistic, after seeing the surface is the failure mode `O22`'s
   depth-measure swap was refused for.
5. **Reporting outcome (a) when §4's ambiguity rule resolves to (b) or (c).**
6. **Extending the grid a third time.** Explicitly forbidden by §4(b) and by the instruction that
   commissioned this run.

---

## 8. Trial cost, and what adoption would mean

**One equity trial, `N` 185 → 186.** Same charge and same reasoning as session 35: the argmax is
taken on the **decide** half and **only the selected width is measured** on the held-out half, so
eight widths do not buy eight looks at the answer. The sweep is the selection step, not eight
tests.

**Nothing here adopts anything.** Even outcome (a) produces a *routed decision*, not a change:
adopting a band width is a **VINTAGE EVENT** under Rule 6 — it closes the current vintage and
resets the five-year forward clock for zero statistical gain. The vintage is **DERIVED** at write
time via `track_meter.current_vintage()` and never assumed (`PT-GAPDUE`).

**Two limitations from session 35 travel with any verdict here:** the band is **already live in
the `taxable` configuration**, so an adopt changes the *default* rather than introducing the band;
and **B13 is only PARTIAL**, so "the book is investable" holds for the categorical screen and not
the liquidity one.
