# PREREG — MB8: MA28's crash flags as a position-SIZING haircut

**Registered 2026-08-19. Committed ALONE, markdown only, as a strict git ancestor of every
measurement commit.** Executes `VALQUO_MASTER_AUDIT_4.md` item `MB8`.

**1 equity trial, booked BEFORE the run (equity `N` 235 → 236).**

**ADOPTION IS A VINTAGE EVENT AND THIS REGISTER DOES NOT ADOPT.** A sizing rule changes the live
scoring path, so an eligible result is recorded **ELIGIBLE and ROUTED TO DON**, never adopted here.

---

## 0. The hypothesis, and why sizing rather than selection

`MA28-CARD` measured a **crash-rate RATIO**, not an alpha: names tripping two or more of Beneish
M > −1.78, Altman Z < 1.81 and top-decile within-date external financing lost more than half their
value over the next quarter at **2.6597% against 0.8743%, ratio 3.0422×**, replicating **3.4209×
early and 2.9321× late**, with every window's observed value beyond the **maximum** of its own
500-draw permutation. The effect **strengthens monotonically with size**, 2.010× in the smallest
quintile to **5.169× in megacaps**.

**A quantity of that shape maps onto HOW MUCH TO HOLD, not onto WHAT TO HOLD.**

**The arm: multiply a flagged top-decile holding's weight by 0.5.** The haircut is **FIXED at 0.5×
before the run and is NOT SWEPT** — sweeping it is the in-search-to-hold-out collapse this project
has already paid for once (+8.43%/yr in-search → −0.04%/yr locked hold-out).

### 0.1 Why this is not `S10-ACCT` in costume — all three differences stated before the run

`S10-ACCT` ran the **exclusion** version and failed on the **portfolio-drawdown** leg, and `S10`
had already measured why that leg can never pass: this book's worst peak-to-trough spans **exactly
one 63-day period on every arm, COVID 2020Q1 at trough index 44 of 69**, which no name-level rule
can move.

1. **Different intervention** — a 0.5× weight, not a deletion.
2. **Different primary statistic** — a name-level crash count in the book, not portfolio max
   drawdown.
3. **The alpha leg is NON-INFERIORITY**, not improvement.

---

## 1. THE ARITHMETIC, DONE FIRST — AND IT SAYS THE BAR IS PROBABLY UNREACHABLE

**A 0.5× haircut can remove at most half of the crash exposure it touches.** So

> **reduction ≤ 0.5 × (flagged share of the book's crash exposure)**

and **to clear a 20% reduction the flagged names must carry ≥ 40% of the book's crash exposure.**

`MA28-CARD`'s own published pooled figures put that share, panel-wide, at **174 of 909 = 19.14%**.
Substituting its measured flagged share of rows (7.36% on eligible rows), flagged crash rate
(2.660%) and kept rate (0.893%):

| construction | reduction at a 0.5× haircut |
|---|---|
| **renormalised (fully invested) — the PRIMARY** | **6.12%** |
| un-renormalised (weight held back as cash) — sensitivity | 9.57% |

**Both are a factor of two to three BELOW the 20% bar.** The register therefore expects the kill
condition to fire, says so before the number is read, and runs anyway for one reason only: **the
primary is measured on the TOP DECILE, not the panel**, and the top decile is a different and
megacap-tilted population where `MA28` measured the ratio at its strongest (5.169×). Whether the
flagged *share of crash exposure* is also higher there is an empirical question and is not
prejudged.

**This bound is quoted with the verdict or the verdict is not quoted.** A kill here is a finding
about **the 0.5×-haircut DESIGN**, not about the flag — `MA28` established the flag on its own
evidence and this register cannot and does not touch it.

---

## 2. The intervention, fixed exactly

* Book: the **top decile** of the deployed composite on `panel_r5r6.pkl`, through the **shipped**
  `quantile_backtest` construction — seven themes at 0.125, `np.argsort(-comp)`,
  `np.array_split(order, 10)`, `buckets[0]`.
* Flags: **imported from `scripts/s10_accounting_veto.py::build_flags`**. The thresholds −1.78 and
  1.81 and the top-decile external-financing rule are **NEVER retyped** — `MA28`'s own test bans
  redefining them and that ban is inherited, because two definitions of one bar is audit `B7`'s
  defect class.
* Weights: `w_i = 0.5` if flagged else `1.0`, then **renormalised so the weights sum to the number
  of holdings** (mean weight 1), which keeps the weighted crash count on the same scale as a count
  and keeps the book **fully invested**.
* **WHY RENORMALISED IS THE PRIMARY, decided in advance:** an un-renormalised book holds cash, and
  cash drag would depress its alpha for a reason that has nothing to do with the flag — it would
  fail the non-inferiority guard rail mechanically. The un-renormalised construction is reported as
  a **declared sensitivity** because it is the more conservative reading of "haircut".

---

## 3. THE PRIMARY, and the kill

**Crash exposure in window W** = `Σ_dates Σ_{i ∈ top decile, fwd_ret_i < −0.50} w_i`, pooled.
Base uses `w_i ≡ 1`; the arm uses the haircut weights.

**`reduction = 1 − arm_exposure / base_exposure`.**

> **KILL: if the reduction is under 20% in EITHER half, the sizing family CLOSES PERMANENTLY.**

Halves are `MA28`'s own — 34 / 34 with the boundary embargoed. The per-date distribution is
reported alongside the pooled figure, and **dates with zero top-decile crashes are counted and
disclosed** (`MA28` reports 20 of 69 such dates panel-wide, so the per-date series is sparse by
construction and the POOLED statistic is the primary for that reason).

---

## 4. THE GUARD RAIL — gating, and it can REJECT on its own

**Top-decile alpha, non-inferiority, against `X7`'s calibrated margin of 1.8629pp.**

> **If the arm's alpha is worse than the base book's by MORE than 1.8629pp annualised, the arm is
> REJECTED regardless of the crash result.** A risk control that costs alpha is a trade, not a free
> lunch, and this register may not make that trade.

**The margin is CURRENT and that is proved rather than assumed.** `MA19` recalibrated it to
**1.8629pp** at `N` = 224. The audit's item says it is *"due a re-derivation at `N` = 234"` — **that
work is already done: `MB31` proved `N` enters a permutation floor ONLY through the CPCV adopt
gate, that the adopt set is identical at 224 and 234, and that no permutation floor can move before
equity `N` = 247.** At `N` = 236 the margin is unmoved. **This register does not re-derive it and
does not need to.**

**A PASS ON THIS LEG IS NOT A FINDING THAT THE COST IS SMALL.** It means *"no alpha loss detectable
at this panel's resolution"* — `X3`'s error, named by `S10` and named again here before the number
exists. It is reported with its MDE (§5) or it is not reported.

---

## 5. THE POWER STATEMENT, BEFORE THE RUN — `RUN_RULES` PART A rule 11, via `MB22`'s gate

The alpha leg is a **paired per-date difference** between two books on one panel. `V2G` established
that **no calibrated floor exists for a paired within-panel difference**, so the bar is the
conventional 2.0 and is **labelled UNCALIBRATED everywhere it appears**.

At n = 69 paired dates, `power_gate` at crit 2.0:

| | SD units |
|---|---|
| **MDE at 80% power** | **0.3419** |
| detection threshold at 50% power | 0.2408 |

The realised per-date SE and the pp-equivalent MDE ship in the artifact. **`V2G`'s own measurement
is the anchor to expect:** it found the HAC SE of a paired annual alpha difference to be
**0.9354pp**, giving a resolution near **1.87pp** — almost exactly the non-inferiority margin, which
means **this design is matched to its bar and has essentially no room to spare.** Quoting the
50%-power figure as though it were the 80% one is the elision `MB22` exists to stop.

**No power statement is offered for the crash leg and the reason is §1:** its outcome is bounded by
arithmetic rather than by sampling error, so an MDE would be the wrong instrument.

---

## 6. THE FAIL-OPEN, STATED IN THE OPEN BECAUSE IT IS THE FAILURE THAT MATTERS

`MA28-CARD`'s `C7`: **25,079 rows — 22.01% — carry fewer than TWO computable inputs and therefore
CANNOT BE FLAGGED AT ALL.**

> **AN UNFLAGGABLE NAME TAKES NO HAIRCUT. THE SIZING RULE FAILS OPEN.**

On a *screen* an unflaggable name failing open is a coverage caveat. **On a sizing rule it is the
whole risk of the design**: the rule silently declines to protect the fifth of the book it cannot
see, and nothing in the output says so unless the register makes it say so. This is the mode this
lane has refused twice before — `O7`'s earnings filter reading *"no date"* as *"no announcement"*
on a non-random tenth of the book, and `MA38`'s missing open interest becoming a zero count.

**And the fail-open is PRICED rather than merely disclosed, from `MA28`'s own artifact: those
25,079 unflaggable rows crash at 0.8134%, against the flaggable-and-kept rate of 0.8928%.** They
are, if anything, marginally *safer* than the names the rule does see and declines to haircut. **So
the fail-open is not leaving a crash-prone fifth of the book unprotected — measured.** That is a
material mitigation and it is stated here so it cannot later be presented as a discovery.

**The arm is re-read on ELIGIBLE ROWS ONLY as a declared sensitivity**, per `MA28`'s `C7`.

---

## 7. REPORTING RULES, inherited from `MA28-CARD` and binding here

1. **QUOTE RATIOS AND BOTH RATES, NEVER DIFFERENCES.** `MA28` measured the base rate moving **4×
   between halves** — kept **0.3413% early against 1.3595% late** — so the absolute gap swings
   **0.86pp → 2.39pp** while the ratio barely moves (**3.42 → 2.93**). *"1.6pp more likely"* is an
   era average describing neither half.
2. **The effect is strongest in MEGACAPS** (2.010× smallest quintile → 5.169× megacap), which is
   where the live hot list actually sits — the one place in this record where a claim is strongest
   exactly where the product is. `V6-B`'s standing caveat points the other way and both must travel
   together.
3. **No claim is made about the flag itself.** `MA28` owns that; this register measures only what a
   0.5× haircut built on it does to a book.

---

## 8. Controls — C1–C4 GATING, computed and READ in their own pass

`--arm` **refuses** without a controls artifact whose `all_gating_pass` is true.

* **C1 — THE PANEL IS THE PUBLISHED OBJECT (gating).** `quantile_backtest` on the deployed seven at
  0.125 must reproduce the record: `top_decile_alpha` **0.07174142332098163**,
  `long_short_tstat` **2.8360640685320595**, HAC **2.6199121240414884**, `monotonicity`
  **−0.8909090909090909**. `MA28` records that this control **actually fired** on its first run —
  nine themes at 1/7 gave alpha 0.0499 against 0.0717, *"a different composite wearing the right
  name"*. Reproduce or abort.
* **C2 — MY DECILE MEMBERSHIP IS THE SHIPPED ONE (gating).** The arm needs per-name membership,
  which `quantile_backtest` does not return, so it is rebuilt from the same primitives. **It is
  then PROVED identical**: the equal-weighted top-decile alpha computed from my membership must
  reproduce `quantile_backtest`'s own `series.alpha` **to < 1e-12 on every date**. **This control
  exists because `MB18` was burned by exactly this two items ago** — a re-derived construction that
  quietly answered a different question, audit `B7`'s class.
* **C3 — THE FLAGS ARE `MA28`'s (gating).** `build_flags` is imported, not redefined; the flagged
  share of panel rows must reproduce `MA28`'s **5.7414%** and its **6,542** flagged-row count.
* **C4 — THE HAIRCUT IS INERT WHERE IT SHOULD BE (gating).** With the haircut set to 1.0× the arm
  must reproduce the base book **bit-for-bit** on every reported field. A sizing arm that moves
  something at 1.0× is not measuring the haircut.
* **C5 — fail-open census (reported).** Count and share of unflaggable top-decile holdings, and
  their crash rate, per window.
* **C6 — size decomposition (reported, no verdict).** The reduction by market-cap quintile, since
  `MA28` measured the effect's gradient and the book is megacap-tilted.

---

## 9. My prior, stated before the run

The audit's is **~50%**, *"and the uncertain leg is the one that decides"*.

| prediction | odds |
|---|---|
| **the crash-count reduction clears 20% in BOTH halves** | **7/93** |
| the reduction clears 20% in EITHER half | 12/88 |
| the measured full-sample reduction lands within ±3pp of the §1 arithmetic (6.12%) | 70/30 |
| the alpha non-inferiority guard rail PASSES | 75/25 |
| the flagged share of TOP-DECILE crash exposure exceeds the panel-wide 19.14% | 55/45 |
| the eligible-rows-only sensitivity does not change the verdict | 85/15 |

**I am far below the audit at 7% and the reason is §1's arithmetic rather than a view about the
flag.** A 0.5× haircut on a flag that fires on ~6–7% of rows cannot remove 20% of a book's crash
exposure unless those rows carry ≥40% of it; `MA28`'s own numbers put that share at 19.14%. **The
audit set a 20% bar and a fixed 0.5× haircut without multiplying them together.** For the bar to be
reachable the top decile would have to more than double the panel-wide flagged crash share, which
is possible but is not what `MA28` measured.

**I expect the guard rail to pass**, because a 0.5× haircut on 6% of holdings is a small
perturbation — and per §4 a pass there means only that no loss is detectable at 1.87pp resolution.

---

## 10. Void conditions

1. **The haircut is swept**, or any value other than 0.5× carries a verdict.
2. **The 20% bar or the 1.8629pp margin is restated** after any number is read.
3. **The alpha leg is reported as an improvement test** rather than non-inferiority, or a pass on it
   is quoted as *"the cost is under 1.86pp"*.
4. **A crash-rate DIFFERENCE is quoted as the headline** in place of the ratio and both rates (§7.1).
5. **The fail-open is not stated** wherever the arm's result is stated (§6).
6. **Gating controls are computed in the same pass as the arm.**
7. **`build_flags`, `beneish_m` or `altman_z` is redefined**, or −1.78 / 1.81 retyped.
8. **The arm is adopted, or any file on a live scoring path is changed.** Eligible → routed to Don.
9. **`MA28_CARD.json` is written to**, or any `MA28` verdict re-opened.
10. **The trial is charged to a domain other than equity, or booked after the run.**

---

## 11. What this register CANNOT establish

* **It cannot show the crash flags do not work.** `MA28` established them; a kill here closes the
  **0.5×-haircut sizing design**, and §1 says in advance that the design is arithmetically
  constrained rather than the signal being absent.
* **It cannot rescue `S10-ACCT`'s drawdown leg**, which `S10` measured to be decided by one
  market-wide quarter.
* **It says nothing about a haircut at any other strength**, by §10.1.
* **It is one panel and one 63-day crash definition.**
