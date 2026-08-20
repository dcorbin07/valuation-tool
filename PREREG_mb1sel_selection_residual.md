# PREREG — MB1-SEL: is the selection residual real?

**Status: BLIND. Committed ALONE, markdown only, zero `.py`, as a strict git ancestor of every
commit that computes any new statistic.** Nothing in this register has been computed. `MB1`'s
decomposition point estimates are published and are quoted below as the *motivation*; **no
uncertainty measure of any kind has ever been attached to the selection residual**, and supplying
one is the entire content of this item.

Deferred here by `HANDOFF_optionsbot.md` §66 and licensed as its own register.

---

## 0. The question, and why `MB1` could not answer it

`MB1` obtained the identity it set out to obtain:

    pick_gap  =  menu_gap  +  selection_residual
                 (DAY)        (CONTRACT)

| window | pick | menu (DAY) | **selection residual** | selection share |
|---|---|---|---|---|
| full | −6.0326pp | −4.7564pp | **−1.2762pp** | 21.16% |
| early | −4.5589pp | −2.8367pp | **−1.7223pp** | 37.78% |
| late | −7.4864pp | −6.3414pp | **−1.1450pp** | 15.29% |

**Every one of those is a bare point estimate.** `MB1`'s register committed no uncertainty measure,
and the interval it did compute afterwards was on the **MEDIAN menu gap**, a different quantity —
so the residual's own sampling variability is **unmeasured**, and "selection carries about a fifth
of the loss and exceeds the 1.00pp bar" is a **post-hoc reading of three numbers with no error
bars**. This register confirms or refutes it properly.

---

## 1. THE STATISTIC IS TAIL-CAPABLE, AND THE MEDIAN IS BANNED BY MEASUREMENT

Long-call returns on this book are bimodal with an enormous mass near total loss. **The median
cannot see the effect being tested, and that is measured rather than argued** — twice:

* **`O17C4`** recorded the "own the event" effect as *"a MEAN effect, not a MEDIAN one"*:
  DTE-matched, median-vs-median was **+0.40pp** while the means separated by **4.79pp**.
* **`MB1`** reproduced it on this exact object: both arms' pooled menu medians sit at about
  **−0.50** (a 0.43pp gap) while the **mean** gap on the *same legs* is **−4.7564pp**.

**So the median is forbidden here as a primary, a secondary or a tie-breaker**, and a test pins
that it is computed nowhere in the arm path.

**PRIMARY: the MEAN selection residual**, in pp, re-derived exactly as `MB1` derived it —
`(mean(alert pick) − mean(control pick)) − (mean(alert menu leg) − mean(control menu leg))`, all
four on the covered entries only, matched by `(ticker, entry, seed)` from the banked legs artifact.

**DECLARED SECONDARIES, carrying NO verdict power:** the same residual with **10% and 20%
symmetric trimmed means**. They are robustness against a handful of extreme legs driving the mean,
they are declared here before any of them is computed, and **they may not flip, rescue or override
the primary's verdict.** A test pins that the verdict reads only the primary.

---

## 2. UNCERTAINTY IS PRE-COMMITTED THIS TIME

**Paired name-year cluster bootstrap**, which is `R3`'s own unit on this book (design effect
**2.1837** against a shuffled-null p95 of 1.1898 — clustering here is measured, not assumed).

* cluster = `(ticker, year(entry))`; `MB1` measured **875** clusters full, **457** early, **445**
  late.
* **PAIRED**: one set of cluster keys is drawn per replicate and applied to **both arms and both
  legs**, so a draw that loads up on a good name loads it up everywhere and common name/period
  effects cancel. An unpaired bootstrap would measure the wrong thing.
* **2,000 draws, seed 20260820**, percentile CI95 `[2.5, 97.5]`.
* A replicate missing any of the four components is **dropped and counted**, never treated as zero.

---

## 3. THE VERDICT RULE — WHAT THE INTERVAL MUST EXCLUDE, FIXED BEFORE ANYTHING IS READ

`MB1`'s register omitted this and that omission is why its closure failed. Three states, mutually
exclusive, evaluated in this order:

**CONFIRMED — selection matters.** ALL of:
1. the CI95 **excludes zero** in the **full sample AND in BOTH halves**;
2. the point estimate has the **same sign** in all three windows;
3. **the materiality bound holds across the INTERVAL, not merely at the point** — the full-sample
   CI95's end *nearer to zero* is beyond **1.00pp** in magnitude.

Condition 3 is `O21-D2`'s lesson taken verbatim: *"a bound has to hold across the INTERVAL, not
merely at the point estimate."* A point estimate of −1.28pp with an interval straddling −0.1pp does
not establish a material effect.

**REFUTED — selection does not matter.** The full-sample CI95 lies **ENTIRELY INSIDE ±1.00pp**.
That is the `O21-D2` shape: not "we failed to find it" but "we have bounded it below the bar the
question was asked at."

**UNRESOLVED — neither.** Everything else, and in particular the case that the CI includes zero
*and* extends beyond ±1.00pp: the design can neither separate the effect from zero nor bound it
below materiality. **Ambiguous against a pre-committed threshold is a NULL** (`RUN_RULES` A6).

**The 1.00pp bar is `MB1`'s own, reused verbatim rather than re-chosen.** Re-picking it now, with
the point estimate already published at −1.28pp, would be choosing the bar around the answer.

---

## 4. THE GATING CONTROL — RANGE RESTRICTION, IN ITS OWN PASS, READ BEFORE THE ARM

`MB1`'s notes flag this and `O10`'s process defect is the reason it gets its own pass: *"C2 and the
outcome statistics were computed in the SAME pass, so it cannot be claimed the control was read
before the numbers."* **Not repeated here.** The arm script **refuses to run** without a passing
control artifact.

**The exposure.** The menu covers **2,446 of 3,870** alert entries (63.20%) and **18,227 of
29,654** control entries (62.49%). The residual is a **difference of differences**, so a coverage
effect that is *constant across the arms cancels exactly*. It is vulnerable only to a coverage
effect that **differs between the arms**.

**C-RANGE, with its bar fixed now.** On banked `pnl_pct`, compute the covered-minus-uncovered mean
shift **separately for each arm**, then their difference:

    differential  =  (covered − uncovered)_alert  −  (covered − uncovered)_control

**VOID if |differential| > 1.00pp** — the same bar the residual is judged against, because a
confound as large as the effect cannot be ruled out as its cause. Reported with both arms' shifts
and both covered/uncovered n, whatever it says.

**C-DISP (reported, no verdict):** the covered and uncovered return **standard deviations** per
arm, so genuine range *restriction* (an attenuating narrowing) is visible rather than assumed
absent.

---

## 5. Void conditions

1. The median computed anywhere in the arm path, or used as a tie-breaker.
2. A secondary reported as, or allowed to override, the primary.
3. The 1.00pp bar changed, or the half boundary re-chosen — it is `MB1`'s **2019-12-12**, taken
   over the covered ALERT set, reused verbatim.
4. The arm run without a passing `C-RANGE` artifact.
5. Differencing anything here against `R2`'s published whole-book **−5.0640pp**, which is a
   different entry set — the scope error this record has paid for repeatedly.
6. Quoting any figure without the alert-days-and-covered-subset conditioning.
7. Reading a CONFIRMED as evidence the alert entry works. **`R2` stands; `O11` binds.**

---

## 6. Scope

The covered subset only — **63.20% and 62.49%** — and **the uncovered remainder is UNMEASURED and
is never read as zero.** Read from the **pinned** harvest freeze via the shared resolver;
`pre_panel_history` filtered. The pick side is banked `pnl_pct` and the menu side is re-simulated
on the freeze; `O21-D2` measured banked-versus-harvest reproduction on this same book at **2,309 of
2,309 exact**, and the difference-of-differences cancels any bias constant across the arms.

---

## 7. Prior, stated as the brief requires

| outcome | prior |
|---|---|
| **UNRESOLVED** | **65%** |
| CONFIRMED | 25% |
| REFUTED | 10% |

**The most likely single outcome resolves neither decision, and saying so in advance is the
point.** The reasoning: `MB1`'s companion interval on the *menu* gap spanned **29.6pp** on the
early half around a −0.73pp estimate, so this book's leg-level noise at the name-year cluster is
very large relative to a 1.28pp residual. REFUTED is priced lowest because it needs the whole
interval inside ±1.00pp while the point estimate already sits at −1.28pp.

Secondary expectations: **E1** the early half's interval is the widest of the three (75%);
**E2** the trimmed means shrink the residual toward zero (60%); **E3** the residual keeps the same
sign in both halves (70%).

---

## 8. Trial cost

**3 options trials, booked BEFORE the arm runs: `N` 305 → 308.** One for the primary mean and one
for each declared trimmed secondary — each is a statistic that could independently be reported, so
each is charged, and **overstating `N` is the safe direction**.

The `C-RANGE` control charges nothing: it scores no hypothesis against a bar about returns.

---

## 9. What each outcome decides, stated before the answer is known

* **CONFIRMED → `MB2`'s grid is UNPARKED and goes to Don.** Selection demonstrably carries a
  material share of the loss, so a search over contract-selection parameters has something to find.
* **REFUTED → contract selection is CLOSED, with the sound argument `MB1`'s kill could not
  supply.** `MB1`'s kill fired on a statistic that could not see the effect and on an inference
  that ran backwards; a bounded interval on a tail-capable statistic is the closure that item
  failed to deliver.
* **UNRESOLVED → NEITHER.** `MB2` stays parked and contract selection stays open. It is **not** a
  licence to re-run this with a different statistic until something clears — that is the search
  this register exists to prevent, and a re-open needs new data or a materially different
  construction, not a second look.
