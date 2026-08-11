# PRE-REGISTRATION — Item C: the COMPLETE bound set for reinvestment Arm B

**Committed alone, before the re-run exists.** No measurement code for this task has been written
at the time of this commit, and no number from any re-run has been seen.

Item C of `HANDOFF_parked_positives.md` §4. Arm B passed all of its original bounds and was
rejected anyway, on harm the register never encoded. That state — *passed every bound, rejected
on a technicality* — is what this document exists to end. Either Arm B clears a bound set that
actually asks whether its output is still a valuation, and ships at its original parameters, or it
fails one and the item closes **REJECTED-COMPLETE**.

---

## 1 · What this is, and precisely what it is NOT

**THIS IS NOT A BLIND PRE-REGISTRATION, AND CLAIMING OTHERWISE WOULD BE THE WORSE VERSION OF THE
ORIGINAL SIN.** Arm B's harm numbers are already published (`HANDOFF_live_data_bugs.md` §8.9,
ledger `OOB3`): **18 negative enterprise values, 16 negative terminal values, 14 DCFs pushed
non-positive, 9 fair values moved UP, 78/241 names changed.** I know what Arm B did before writing
a single bound below. Any claim of blindness here would be false.

What this document *can* honestly claim, and does:

* It is committed **alone, in its own commit, before the re-run** — so no threshold can move after
  seeing the re-run's numbers. That is the property that makes the verdict mechanical.
* **Bounds C1–C3 have no tunable threshold at all.** "The output is still a number" admits one
  setting. There is no version of them I could have chosen to change the answer.
* The two bounds that carry real freedom — **C5** (blast radius) and **P2** (leave the capex-boom
  names alone) — are derived from stated principle, and for each I state **the range over which
  the verdict is invariant**, so the reader can check the answer does not rest on my choice of
  number. If a verdict ever turns on the exact value of C5 or P2, that verdict is not usable and
  this document says so in advance.

**Retuning is forbidden.** Arm B runs at the parameters fixed in `HANDOFF_live_data_bugs.md` §8.3,
i.e. `REINVESTMENT_FLOOR_MODE = "persistent"` with the shipped code path unchanged. No parameter
moves. A failure at the stated value is a REJECTION, not an invitation to adjust.

---

## 2 · The dataset — and an honest deviation from the brief

**The original 2026-08-05 241-name pickle is UNRECOVERABLE.** Searched before writing this: the
repository, both `data/` trees (worktree and primary checkout), all three tracked handoff zips,
and every on-disk cache — `screener.db.fundamentals`, `live_cache/served.db.fundamentals` and
`app.db` are all **0 rows**. It was a session-local artifact and no code in the repository rebuilds
it. The task asked for the re-run "on the 241-name pickle"; that is not possible, and inventing a
substitute silently is exactly the class of move this project logs corrections about.

**Substitute, fixed here in advance:**

* **Universe = the 191 bundled tickers (`valuation.screener.universe.bundled_tickers()`, a fixed
  in-repo artifact) PLUS the seven foreign filers the Part 8 record itself names in its two
  decisive populations: BHP, E, PBR, TTE, RIO, NVO, CNI.** Total **198**.
* **There is no discretionary name selection.** The rule is "every bundled ticker, plus exactly the
  names the published record lists as decisive that the bundled list lacks". Both inputs are
  fixed documents. I am not choosing names.
* Coverage of the record's own sets by this universe, measured before writing this and reported so
  the substitution is checkable: **33/33 of the decisive set** (14 flat-revenue + 19 capex-boom)
  and **10/10 of the names the record singles out for harm**. Of the seven added foreign names,
  **five are flat-revenue** (the population the fix is supposed to *help*) and two are capex-boom,
  so the addition is not tilted against Arm B.
* **Snapshot date: 2026-08-11, freshly fetched.** It is NOT the 2026-08-05 data. Absolute figures
  will differ from the record and are not comparable to it.

**This substitution is sound because every bound below is SELF-RELATIVE** — each compares the
treated run against the control run *on the same snapshot, in the same process, from the same
`CompanyData` objects*. None compares against a number from 2026-08-05. The verdict is therefore
well-defined on whatever snapshot is used, and the loss is comparability of magnitudes, not
validity of the test.

### 2.1 VOID preconditions — the vacuous-pass guard

A throttled fetch returns partial `CompanyData` without raising, and a name with no data fails the
`net_capex > 0` gate and silently leaves the treated population. **Every Group-1 bound below passes
trivially on an empty population.** So, committed now:

The run is **VOID — not a pass** — unless all of these hold, and a VOID result is reported as VOID:

* **V1** ≥ **95%** of the 198 names fetch with a non-null `revenue`.
* **V2** the treated set (non-financial, `capex − D&A > 0`) is ≥ **80** names.
* **V3** the decisive set (treated, undercharged > 5% of revenue) is ≥ **20** names.
* **V4** the control arm reproduces the shipped `"off"` behaviour exactly — see H1.

---

## 3 · The arm

**ARM B — persistent floor, explicit years AND terminal**, exactly as §8.3 fixed it:
`reinvest_t = max(growth_t, nc · rev_t/rev_0)` with no decay, and the terminal charge becomes
`max(g/ROIC · nopat_next, nc · rev_term/rev_0)`. Shipped code, `REINVESTMENT_FLOOR_MODE`
= `"persistent"`. Control = `"off"`.

Both arms are valued from **the same in-memory `CompanyData` objects, one process, one fetch**, so
the only difference between the two runs is the mode. Beta and macro inputs are resolved once and
reused, so they cannot differ between arms.

---

## 4 · THE COMPLETE BOUND SET

Twelve bounds in four groups. **Group A is the original register, carried verbatim.** Groups B–D
are what it missed. A bound is HELD or VIOLATED; there is no partial credit.

### Group A — the original bounds, unchanged (`HANDOFF_live_data_bugs.md` §8.4–8.5)

> **A COUNT DISCREPANCY IN THE RECORD, NOTED NOT RESOLVED:** §8.9 says Arm B "passes ALL SIX
> pre-registered bounds", and §8.4–8.5 define **seven** (F1–F4, H1–H3), which is also how many
> rows the Item C scorecard has. I carry all seven. Nothing turns on it — Arm B held all seven —
> but "six" is repeated in two places and is wrong by one.

* **F1** — treated names with roughly flat forecast revenue (`|rev_last/rev_1 − 1| ≤ 5%`) are
  charged year-1 reinvestment **within ±25%** of observed net capital spend.
* **F2** — the count of names undercharged by > 5% of revenue falls to **≤ 5**.
* **F3** — the count of treated names with **negative** modelled reinvestment falls to **0**.
* **F4** — decisive-set terminal FCFF falls by a median of **at least 5%**.
* **H1** — the control group is **BIT-IDENTICAL**: every untreated name's fair value, WACC, score,
  confidence and published flag unchanged to the last digit.
* **H2** — published/withheld flips are **zero in the control**.
* **H3** — the decisive set's **median fair value falls**.

### Group B — output validity. THE MISSING GROUP. Every one of these is what Arm B failed.

The principle, and it is the whole of Item C: **my bounds asked whether the number moved in the
right direction and never asked whether it was still a number.**

* **C1 — enterprise value stays positive.** Of the names whose EV was positive under control,
  **≥ 99%** must still have a positive EV under Arm B. *(Inventory's figure. With a treated set of
  order 100, this permits at most one violation.)*
* **C2 — terminal value stays positive.** For **every** name whose control terminal value was
  positive, the treated terminal value is positive. **Zero violations permitted.**
* **C3 — the DCF stays positive.** For **every** name whose control DCF was positive, the treated
  DCF is positive. **Zero violations permitted.**
* **C4 — no fair value moves UP.** A reinvestment *charge* that raises a valuation has
  double-counted somewhere. **No name's published fair value may rise by more than 1%** against
  control. *(The 1% is float/renormalisation tolerance, not a budget: the record's own violations
  were +121%, +92%, +73%. The count of names rising by >0% is reported alongside, for diagnosis.)*
  This bound is **diagnostic as well as a guard** — `blend._usable` drops a non-positive lens and
  renormalises, which is the mechanism by which charging *more* raises the answer.
* **C5 — bounded blast radius.** The number of names whose fair value changes at all must not
  exceed **1.5 × the size of the decisive set** measured on the same snapshot.
  *Rationale, fixed in advance:* the decisive set is the target population; a fix may touch its
  target plus limited spillover, and without a stated ceiling "it changed a lot" is unfalsifiable
  in both directions. It is expressed as a multiple, not a count, so it self-scales to a universe
  of 198 rather than 241 and cannot be gamed by the substitution in §2.
  **Invariance:** the recorded Arm B ratio is 78 changed against a 33-name decisive set = **2.36×**,
  so the verdict is unchanged for any multiplier in **[1.0, 2.3]**. If the re-run lands inside a
  band where the multiplier decides the answer, **C5 is reported as INDECISIVE and carries no
  verdict weight**, and the verdict rests on the other eleven.

### Group C — the fix must reach where the defect lives, on the right population

* **P1 — the target is the flat-revenue population.** F1 and F2 above already state it; recorded
  here so the target is explicit rather than implied.
* **P2 — the capex-boom population is LEFT ALONE.** For names in the capex-boom population — those
  whose spend is growth capital already priced through the revenue path — **modelled year-1
  reinvestment may not rise by more than 10%** against control.
  *Rationale:* a single pooled bound cannot distinguish a fix from a double-count; §8.10 measured
  that the 33-name decisive set is two populations and only one has the defect.
  **Invariance:** ORCL's net capex is 68.8% of revenue against revenue growth of 3.1×, so Arm B
  floors these names far above their growth charge; the verdict is unchanged for any tolerance in
  **[0%, 50%]**. The realised distribution is reported so this is checkable.
  *Population rule, fixed now:* a treated name is **capex-boom** if its forecast revenue is not
  flat (`|rev_last/rev_1 − 1| > 5%`, the complement of F1's own test) and it is undercharged by
  > 5% of revenue; **flat-revenue** if it is undercharged and its forecast revenue is flat. This is
  the record's own split rule, restated mechanically — no name list is hard-coded.

### Group D — the controls that already worked. Kept.

* **H1** and **H2** above. They held perfectly for both arms and the gate *is* the control group,
  so they are true by construction; the measurement confirms the construction.

---

## 5 · The verdict rule — mechanical, no judgement

* **ALL TWELVE HELD → Arm B SHIPS**, at its original parameters, with labels and values per the
  original scope (`REINVESTMENT_FLOOR_MODE = "persistent"`).
* **ANY BOUND VIOLATED → the item closes REJECTED-COMPLETE.** Not "rejected on a technicality":
  rejected against a bound set written down before the run and published whole.
* **Any VOID precondition unmet → VOID.** Reported as VOID, never as either of the above.
* **C5 INDECISIVE** (see above) does not block a verdict; it is excluded and the remaining eleven
  decide. Any *other* bound is decisive.

No bound may be added, removed or reworded after this commit. If the re-run exposes a thirteenth
thing worth bounding, it is recorded as a finding for whoever re-opens it — **not folded into this
verdict**, which is precisely the error being corrected.

---

## 6 · Expectation, written down first

**Arm B fails C1, C2 and C3, and the item closes REJECTED-COMPLETE. Confidence 90/10.**

This is a weak prediction and is labelled as such: the original run already published 18/16/14
violations of exactly these three on a different snapshot, so I am predicting a repeat, not
forecasting an unknown. The prediction with actual content is the second one:

**Arm B also fails C4 and P2 — 60/40.** C4 depends on the blend's renormalisation firing on this
snapshot's names, and P2 on the capex-boom population reproducing under a fresh fetch. Neither is
guaranteed by the record. *(This project's directional calls have been wrong more often than
right; the point of writing it down is that it keeps being wrong.)*

---

## 7 · What voids this run

* Any precondition in §2.1 unmet.
* Any change to `valuation/engine/dcf.py`'s floor arithmetic between this commit and the run.
* Arms not valued from the same `CompanyData` objects in the same process.
* Any threshold in §4 edited after this commit.

## 8 · Trial cost — ZERO, and the reasoning

Equity `N` does not move. This re-scores **one already-charged arm** (`OOB3`) at **unchanged
parameters** against **more** bounds. It searches nothing: adding bounds to a fixed candidate can
only move a verdict from pass toward fail, never the reverse, so it cannot manufacture
significance. Same reasoning as session 10's HAC-floor calibration, which also charged nothing.
