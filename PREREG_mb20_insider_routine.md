# PRE-REGISTRATION — `PKG-MB20`: ROUTINE vs OPPORTUNISTIC INSIDER TRADES

**Committed BLIND and ALONE. Markdown only, zero `.py`, a strict git ancestor of every commit
that computes an outcome.** No arm runner exists at the time of this commit. The equity trial is
booked in its own commit, after this one and before any runner.

**Doctrine §3a class: a RE-MEASUREMENT of a shipped input, not a new signal.**

---

## 0. WHAT THIS IS, AND WHOSE DESIGN IT EXECUTES

`MA57` recorded this design on 2026-08-16 and **did not run it**; its ledger row reads
`DESIGN-RECORDED - NOT RUN`. It also refuted the master audit's stated blocker: the audit claimed
the columns *"cannot be built without adding them and re-exporting while the Sharadar entitlement
is live"*, and `MA57` measured them **already present on the export on disk**. This register
executes that design.

The subject is the **`insider` theme**, which this record has flagged repeatedly as the weakest
thing still carrying a full 1/7 of the deployed composite:

* its theme IC is **-0.2259**, indistinguishable from zero and the only negative theme;
* `CLAUDE.md` records that on three identical-data runs it returned **-0.34, +2.69 and -0.43**,
  i.e. *"this theme's t is not a measurable quantity"* — though the held-out verdict was
  `rejected` on all three, and `S3`'s `C1` later reproduced the published record exactly;
* the pure indicator *"has an insider score at all"* carries **more** forward-return information
  (median IC +0.01345, *t* +1.4471) than the score's **direction** does. Neither is significant,
  and **that comparison is the point.**

---

## 1. THE HYPOTHESIS, AND THE RULE, STATED ONCE

Cohen-Malloy-Pomorski (2012, *Decoding Inside Information*, JF): insiders who trade on a
predictable schedule carry no information, and removing them sharpens what is left.

> **THE RULE.** A trade by insider `o` in ticker `t`, in calendar month `m` of year `y`, is
> **ROUTINE** if that same `(t, o)` pair also traded in month `m` in years `y-1` **AND** `y-2`.
> Otherwise **OPPORTUNISTIC**. Three consecutive years.

**IT IS POINT-IN-TIME BY CONSTRUCTION AND NOT BY A FILTER.** The test looks only at years
**strictly before** the trade's own, so a trade can never be labelled using anything that had not
already happened when it was made. There is no `as_of` parameter and nothing to get wrong: the
routine label becomes available exactly when the third repeat occurs.

**DECLARED DIRECTION: filtering routine trades IMPROVES the composite.** A register that would
accept either sign is not a test.

---

## 2. THREE PREMISE CORRECTIONS, ALL MADE BEFORE THIS REGISTER WAS COMMITTED

### 2a. `MA57`'s published 48.72% is a FOUR-year figure, and the rule is THREE

`MA57`'s classifier tests `all((y - dd) in ys for dd in (1, 2, 3))` — year `y` **plus the three
before it**, i.e. four consecutive years, one stricter than Cohen-Malloy-Pomorski.

**REPRODUCED EXACTLY AS THE INSTRUMENT CHECK:** under `MA57`'s own rule this register's
classifier returns **42,537 routine pairs of 87,318 = 0.48715**, against `MA57`'s published
**42,537 / 0.4872**. The pair count agrees to the unit, so it is the same object and **only the
rule differs**. Under the three-year rule the identical population reads **52,798 / 87,318 =
60.47%**.

**Anyone carrying 48.72% forward as "the Cohen-Malloy-Pomorski share" is quoting a different
rule.**

### 2b. The briefed coverage kill has a ZERO answer on the population that matters

The brief sets a coverage kill on *"`transactioncode` absent on 27.4% of rows — measure who
drops"*. **The classification does not use `transactioncode` at all.** It needs `ownername`
(missing on **0** of 5,636,964 rows) and `transactiondate`.

Measured: `transactiondate` is missing on **1,544,487** rows against `transactioncode`'s
**1,544,490** — three rows apart, so nearly co-missing but **not identical masks**. And decisively:

* rows the shipped score can value: **3,454,363 (61.28%)**;
* of those, rows this rule can classify: **3,454,363 — every one**;
* rows scoreable but unclassifiable: **ZERO**.

**So classification coverage on the arm's own population is 100.00%.** The 27.4% is a fact about
the **export**, not about the arm — `O-1`'s lesson, which returned 0.19% power by carrying a
coverage figure across populations, and `S25`'s *"two nearly-equal percentages on different
objects"*. The rows that cannot be classified are **exactly the rows the score already skips**.

**The kill is kept anyway** (§7 `K1`), because a coverage kill that costs nothing today is the
one you want present the day the export changes.

### 2c. An instrument check that reproduces two independent published counts

The score's valuable-row count implies **2,182,601** rows skipped for carrying neither price nor
value — **`V6-B`'s published figure exactly**. And on the panel, **94,660** cells carry a shipped
insider score — **the count `S3`'s `C3` reports independently**. Two prior items' numbers
reproduced from a fresh instrument, which is what licenses everything below.

---

## 3. THE MEASUREMENTS THAT SET THE BARS, TAKEN BEFORE THE BARS WERE WRITTEN

`W-28` died because a pre-committed bar could not be reached on this account at all, and `W-1`'s
own `K2` was set from the wrong arm's figure and **would have killed a legitimate register**.
Both bars below are therefore written with the distribution already printed.

**THE BITE — the fraction of scored cells whose insider score MOVES:**

| | |
|---|---|
| panel cells | 113,945 |
| cells with a shipped insider score | **94,660** |
| cells whose score MOVES | **49,613 = 52.41%** |
| cells the variant alone cannot score | **2,583 (2.73%)** |
| routine share of scoreable insider rows | **36.76%** (1,269,833 / 3,454,363) |

Score delta: mean **-0.4815**, median **+0.0785**, p05 **-32.21**, p95 **+26.74**, **41.80%
negative**. **The intervention is nowhere near inert and moves in both directions**, so a null
here can be read as *"the hypothesis is false on this panel"* rather than *"nothing was done"*.

**THE COSTUME SUBJECT — mean per-date |Spearman| of the intervention against each theme:**

| theme | which names MOVE | how much they move |
|---|---|---|
| `size` | **0.1281** | 0.0561 |
| `quality` | 0.1036 | 0.0688 |
| `capital_discipline` | 0.0653 | 0.0254 |
| `momentum` | 0.0491 | 0.0551 |
| `value` | 0.0458 | 0.0394 |
| `institutional` | 0.0414 | 0.0395 |
| `insider` | 0.0556 | **0.4469** |

**The 0.4469 against `insider` itself is MECHANICAL and is not a costume** — the delta *is* a
change in that score, so it must correlate with its level. It is tabulated so a reader does not
discover it and misread it as the kill firing.

---

## 4. THE ARMS — one build, two scorings, a provably identical row set

**`A_BASE`** — the shipped composite, unchanged.
**`A_OPP`** — identical in every respect except that the `insider` theme is computed from
**opportunistic rows only**.

Both are produced by **ONE panel build in one pass over the same rows from the same provider**,
differing in the insider row set alone. Three builds would let the row set drift and confound the
hypothesis with whatever else moved (`S25-REPAIR`'s construction, and `W-1`'s).

**THE FALLBACK IS PRE-COMMITTED AND IT IS `W-28`'s CLOSING LESSON APPLIED DIRECTLY.** On the
**2,583 cells** where every row in the window is routine, `A_OPP` **falls back to the incumbent
score**. `W-28` established that replacing an input wherever the new one is absent *silently
becomes that input's REMOVAL arm* — and on this composite removal was already measured as
harmful. With the fallback the paired difference is **exactly zero** on those cells, the
population is **unchanged**, and a verdict is attributable to the hypothesis rather than to a
coverage hole.

**PRE-DECLARED SENSITIVITY, CARRYING NO VERDICT:** the same arm with those 2,583 cells scored
`None` instead. It is a **different hypothesis** (filter *and* abstain) and quoting it as the
result is a void condition.

**`composite_from_frame` IS CALLED, NEVER RE-IMPLEMENTED** (`B7`), and `C-IDENT` gates that the
composite reproduces it elementwise at max |Δ| 0.000e+00 — **proved NON-VACUOUS** by perturbing
one cell by 1e-12 and requiring the identity to break, and by refusing an empty comparison rather
than scoring it perfect (`MB21`'s `C1` once scored 0.000e+00 by comparing nothing).

**THE PRODUCTION CHANGE IS OPT-IN AND INERT BY DEFAULT.** `_KEEP["insiders"]` gains
`ownername` and `transactiondate`, and `build_fundamental_panel` gains an opt-in flag that emits
the second insider column. With the flag off the builder is **bit-identical**, which `K4` proves
on the real panel rather than by assertion — the shape `W-1`'s `sector_at` hook used.

---

## 5. THE GRAVEYARD, ARGUED PAST IN WRITING

* **`S3` REJECTED THREE INSIDER REBUILDS** on this exact gate (drop the `buys` bonus; scale by
  market cap; split into two z-scored inputs). **Every one of them changed the FORMULA on the
  same rows. This changes the ROW SET under the same formula** — a different object, and the one
  the literature actually names. `S3`'s own §NOT-DONE does not close it.
* **`R6` WITHDREW ON A SIZE COSTUME at 0.6114.** Measured in advance here at **0.1281**, and the
  bar is `R6`'s own **0.60 reused verbatim** rather than re-chosen (§7 `K3`).
* **`V6-B` arm 3** (dip × insider open-market buying) was NULL — an **interaction** built from
  code `P` only, not a re-measurement of the theme.
* **THE FOUR ORTHOGONALITY CORPSES DO NOT BIND, and this register does not invoke them.** `U2`,
  `MA31`/`MA32`, `MA58` and `MB18` were all motivated by *"structurally orthogonal to the
  incumbents"*, all confirmed orthogonal, and not one cleared. **This item's motivation is not
  orthogonality** — it does not add a column, it removes rows from one that already ships. If the
  case for it were orthogonality it would be killed here on that ground alone.
* **`MB16`'s dedup defect**: ONE log row, verdict edited into that same cell in place.

---

## 6. THE GATE — the shipped one, verbatim, and the bars it is judged against

`holdout_compare_panels`, **both halves, boundary embargoed at 2017-07-20**, under **both
weightings** — `DEPLOYED` (the seven weighted themes, which **carries the verdict**) and `FLAT` —
both **IMPORTED** from `SECTOR-NEUTRAL-B6` rather than retyped (`W-1`'s `K4` fired against a
correct panel for exactly that error).

**ADOPT-ELIGIBLE requires, in BOTH halves and on the DEPLOYED weighting:**

> Δ long-short *t* **> +0.25** **AND** Δ top-decile alpha **> +100 bps**

**the same margins `SECTOR-NEUTRAL-B6`, `S3` and `W-1` committed, reused verbatim.** Anything
else is `REJECTED`. Ambiguity against a pre-committed threshold is a NULL, never a judgement
(`RUN_RULES` A6).

**X7's calibrated floors are LEVEL floors and are quoted for each arm's own level, labelled.** At
the post-booking `N` = 248 they are `W-1`'s re-derived values — long-short naive **2.070231**,
long-short HAC **2.056680**, top-decile alpha HAC **1.826210**, theme IC *t* **2.7072**.
**NO CALIBRATED FLOOR EXISTS FOR THE PAIRED DIFFERENCE** — `V2G` established it and `R1-VAR`
re-confirmed it — so every critical value applied to a difference is **LABELLED UNCALIBRATED**.

---

## 7. KILLS — declared before arming, run in their OWN pass, READ before any arm

`--arms` **refuses** without a passing kills artifact (`O10`'s process defect: a gating control
and its outcomes must not be computed in one pass).

| kill | fires when | why |
|---|---|---|
| **`K1` COVERAGE** | classification coverage on the arm's own scored rows **< 0.95** | measured 1.0000; kept for the day the export changes (§2b) |
| **`K2` BITE** | fewer than **5%** of scored cells move | an inert intervention cannot return an interpretable null (`W-28`) |
| **`K3` SIZE COSTUME** | mean per-date \|Spearman\| of *which names move* against `size` **> 0.60** | `R6`'s own bar, reused verbatim; measured 0.1281 |
| **`K4` FIDELITY** | the base arm fails to reproduce the published record | `MA28`'s C1 and `MB8`'s C1 both fired in real life; also proves the `_KEEP` and flag changes are inert |
| **`K5` LOOK-AHEAD** | any trade is labelled using a year **at or after** its own | the whole rule is that the label is observable when the third repeat occurs |

`K4`'s targets are the shipped record: `top_decile_alpha` **0.07174142332098163**,
`long_short_tstat` **2.8360640685320595**, `long_short_tstat_nw` **2.6199121240414884**,
`monotonicity` **-0.8909090909090909**.

---

## 8. POWER — the arithmetic fixed now, the numbers measured on this arm

`MB22`'s two vocabularies, **both reported with any verdict or the verdict is not quoted**:

> `MDE_50% = crit × se` and `MDE_80% = (crit + 0.84) × se`

**THE `se` MAY NOT BE BORROWED AND WILL NOT BE.** `MB8` measured a paired HAC se of **0.1106pp**
and `V2G` **0.9354pp** — **8.5-fold apart** — for the same reason: a paired difference between
two highly correlated books is measured far more precisely than one between two different books.
`W-1`'s **0.001600** is likewise a different perturbation (a sector relabel touching 4.4% of
cells) and **is cited here only to say it will not be used.** This arm measures its own.

Both critical values are reported: the conventional **2.0** and the honest hurdle at the
post-booking `N`, **3.3206712412296953**. Both are **UNCALIBRATED** for a paired difference.

---

## 9. THE HONEST PRIOR, STATED BEFORE THE RUN

**ADOPT-ELIGIBLE: 12%.** Reasons, in the order they weigh:

1. **`S3` already rejected three attempts to improve this theme on this gate**, and the composite
   has never adopted anything the CPCV gate was offered.
2. **The theme being sharpened carries essentially no signal to sharpen** — IC *t* -0.2259, and
   its own presence indicator carries more information than its direction.
3. Against that, **the effect is real in the literature and this is the first attempt on this
   panel that changes the row set rather than the formula**, and the bite is large (52.41%).

**Expectations, scored afterwards:** (1) REJECTED, 88%. (2) `K3` does **not** fire, 90%.
(3) The two halves **disagree in sign** on at least one metric, 60% — this record's most repeated
pattern. (4) The variant's own long-short HAC *t* stays **below** the incumbent's 2.6199, 65%.
(5) The paired alpha difference is **not separable from zero** at its own 80%-power MDE, 70%.

---

## 10. VOID CONDITIONS

1. Quoting the `None`-abstain sensitivity (§4) as the result.
2. Changing `CONSECUTIVE_YEARS`, the 90-day window, the fallback rule or any bar after seeing an
   outcome. The bars in §6 and §7 are the register's; **a successor may not relax a pre-committed
   bar after watching it fail** (`W-28`'s §6 rule).
3. Sweeping the rule over 2/3/4/5 consecutive years. **Exactly one rule is registered.** `MA57`'s
   four-year variant is reported in §2a as an instrument check and carries **no verdict**.
4. Quoting a subset of the four gate cells (2 weightings × 2 halves). All four are reported.
5. Reading a `K3` pass as evidence the intervention is size-neutral **in the composite** — it is
   a statement about which names move, nothing more.
6. Reporting any verdict without its MDE at both vocabularies (§8).

---

## 11. WHAT IT ADOPTS, AND WHAT IT DOES NOT

**ADOPTS NOTHING.** `CONFIG` is untouched and no file under `valuation/screener`,
`valuation/web` or `valuation/engine` changes. **An adopt-eligible result is recorded
`ELIGIBLE, NOT ADOPTED` and ROUTED TO DON**: changing a theme's construction is a **vintage
event**, it resets the five-year forward clock, and it is not this register's decision.

**Also not done, named so it is not mistaken for done:** no second window, no magnitude variant,
no purchases-only construction (the routine share there is **2.72%** and would be a different and
far weaker arm), `S3` is not re-opened, and **`MA57`'s ledger row is not edited** — its
`DESIGN-RECORDED` status and the correction to its 48.72% are relayed, not overwritten.

**Trial cost: 1 equity trial**, booked in its own commit before any runner exists.
**No floor moves at `N` = 248**: `MB31`'s next adopt-set change is **seed 1017 at `N` = 688**,
441 trials of headroom, so the bounded re-derivation `W-1` owed at 247 is not owed again here.
