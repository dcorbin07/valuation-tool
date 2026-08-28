# PRE-REGISTRATION — W-1: SECTOR-NEUTRAL RANKING, RE-RUN ON THE POINT-IN-TIME SECTOR MAP
## The re-open `SECTOR-NEUTRAL-B6` named for itself, run on the map it said it needed — and nothing else

**Registered 2026-08-28. Committed ALONE, markdown only, zero `.py`, a strict git ancestor of every
commit that computes an outcome statistic. 2 equity trials, booked in their own commit BEFORE any
arm runner exists: equity `N` 245 -> 247, hurdle 3.3170041 -> 3.3194543.** Counters re-read from
`research_log.detail()` rather than quoted. **ADOPTS NOTHING** — sector-neutral shipping is a
vintage event and Don's decision.

---

## 0. WHAT THIS IS, AND THE ONE THING IT IS NOT

`SECTOR-NEUTRAL-B6` **closed sector-neutral ranking permanently** and named exactly two routes
back. Its own words: full sector-neutral ranking *"may NOT be re-run as a re-run"*, and re-opening
requires **new data** — **`S25`, a genuine point-in-time sector map**, TICKERS being *"today's
classification and the one non-point-in-time input in the panel"* — **or** a materially different
construction (`S15`, since rejected).

**`S25` built that map.** So this is not a second attempt at a rejected hypothesis; it is the
pre-committed re-open condition being met. **The comparison is `SECTOR-NEUTRAL-B6`'s own, verbatim
— the shipped `holdout_compare_panels`, both halves, both weightings, the same margins — and the
only thing that changes is the sector column it groups on.** Anything else would make it a
different register and forfeit the re-open.

**THE ONE THING IT IS NOT: a claim that a point-in-time map makes sector-neutral work.** The prior
is hostile and §7 says so.

---

## 1. NON-BLINDNESS, DISCLOSED HERE RATHER THAN DISCOVERED LATER (`V6-OPT` §0.5's shape)

**Blind to the OUTCOME. Not blind to two pre-outcome measurements, deliberately, and both were
required before a bar could honestly be written.**

1. **The floor re-derivation (§3).** Booking this register's 2 trials lands equity `N` on **247**,
   which `MB31` names as the exact point where seed 1003 flips the CPCV adopt gate. Writing bars
   without knowing whether the floors move would be writing them against numbers about to change.
2. **The coverage census (§4).** **`W-28`'s closing sentence is the reason:** *a pre-committed bar
   the account structurally cannot clear is a register that can only ever void.* `W-28`'s `K1`
   died on a 90% dated-linkage bar no dated route on this account can reach. **So this register
   measures its instrument's reach FIRST and sets its bar AFTERWARDS, with the distribution
   printed.**

**No composite has been scored, no arm computed, and no relationship between any sector column and
`fwd_ret` exists anywhere yet.**

---

## 2. THE ARM — one column changes, nothing else

| | |
|---|---|
| incumbent | the shipped composite, `sector_neutral=False`, deployed weights |
| arm | **identical**, `sector_neutral=True`, grouping on the **point-in-time** sector |
| the sector column | `S25`'s `SectorMap.at(ticker, date)`, state `OK` only |
| a `NOT_COVERED` cell | **keeps the panel's own sector and is never blanked** — `S25-REPAIR` measured that both engine dicts FAIL OPEN, so blanking hands the row the middle of a 2.70x range rather than abstaining |
| universe, dates, weights, rebalance rule, standardiser | **unchanged** |

**Both weightings are scored, as `SECTOR-NEUTRAL-B6` did**: the deployed vector and flat 1/7. A
verdict resting on one weighting is not that register re-run.

**`TAXONOMY_REVISIONS` ARE HONOURED, NOT COUNTED.** GICS separated **Real Estate in 2016** and
**Communication Services in 2018**. Those are **provider paperwork, not company reclassification
events**; `sector_map` flags them and this register reports them as their own line rather than as
evidence that a name changed sector. **A register that counted them as reclassifications would be
measuring an index provider's filing schedule.**

---

## 3. THE FLOORS AT `N` = 247 — RE-DERIVED, BOUNDED, AND ALL THREE MOVE

`MB31`'s rule: `N` reaches a placebo floor **only** through the CPCV adopt gate, because an
adopting draw is scored under the CHALLENGER's weights and a non-adopting one under the BASE
weights. Seed **1003** flips OFF at exactly 247.

**`MA19`'s method, bounded to ONE re-score rather than a sweep** — and the rank check is what
established it could not be skipped: *"whether a floor moves depends not on HOW MANY draws flip but
on WHERE THEY SAT."* A p95 over 100 draws is set by the 5th-and-6th largest. **Seed 1003 sits at
rank 4 / 4 / 6, and IS the #6 draw on top-decile alpha HAC.**

| floor | at `N` = 245 (published) | **at `N` = 247** | move |
|---|---|---|---|
| long-short naive | 2.143721 | **2.070231** | **−0.073491** |
| long-short HAC | 2.283684 | **2.056680** | **−0.227004** |
| top-decile alpha HAC | 2.054039 | **1.826210** | **−0.227829** |

**THE INSTRUMENT IS CHECKED BEFORE IT IS BELIEVED: the `N` = 245 column reproduces the record's
published floors exactly** (2.1437 / 2.2837 / 2.0540), which is what licenses the 247 column.

* **ALL THREE MOVE, AND ALL THREE MOVE DOWN — the permissive direction.** **NO SHIPPED CLAIM
  CHANGES SIDE**: the headline long-short naive 2.8361, HAC 2.6199 and alpha HAC 4.3762 clear both
  the old and the new floors. **Nothing is retracted.**
* **THE MECHANISM REPRODUCES `X7` INDEPENDENTLY.** Seed 1003 scores `ls_t` **1.404770** under base
  weights and **2.550756** under the challenger's — **+1.146 of *t* from adoption alone**, against
  `X7`'s post-hoc *"CPCV adoption manufactures ~+1.4 of long-short t out of nothing"*. Two
  routes, one number.
* **THIS IS THE FIRST BOOKING IN THIS PROJECT'S HISTORY TO MOVE ALL THREE FLOORS.** Session 12
  warned the floors surviving an `N` change was *"luck, not design"*; `MA19` watched the luck run
  out on one floor. Here it runs out on all three.

**Consequence for this register, stated plainly: NONE of these floors is W-1's gate.** §5's gate is
a **MARGIN** on a paired difference, which is `SECTOR-NEUTRAL-B6`'s own. The floors are reported
because any LEVEL quoted alongside must be read against the right bar, and because the record's
published table goes stale the moment this books.

---

## 4. COVERAGE — ON THE ARM'S OWN POPULATION, BEFORE ANY BAR IS SET

**The population is the 113,945-cell METRICS panel the sector-neutral arm re-ranks.** Neither
published figure may be inherited, and the record already flags why: `S25`'s **94.8%** is measured
on the **S23 VALUATION panel** (2,441 tickers) and the WRDS census's **94.9%** is `ticker -> gvkey`
coverage on the metrics panel — *"two nearly-equal percentages on different objects"*. `O-1` lost
its power to exactly this substitution. **Re-measured here:**

| quantity | measured |
|---|---|
| cells resolving to state `OK` | **107,369 of 113,945 = 94.23%** |
| names ever resolving | **2,305 of 2,531 = 91.07%** |
| states returned | `OK` 107,369 · `NOT_COVERED` 6,576 · **`UNMAPPED` 0 · `AMBIGUOUS_TICKER` 0 · `BEFORE_GICS` 0** |
| **per-date coverage** | **min 0.9010** · p05 0.9143 · median 0.9460 · max 0.9698 |
| PIT sector disagreeing with TODAY's | **14,181 of 107,369 cells = 13.21%** |

**THE BAR, SET AFTER THE MEASUREMENT AND WITH THE DISTRIBUTION IN VIEW — `W-28`'s lesson applied
rather than repeated.** The worst rebalance date resolves **0.9010**. **A 90% per-date bar is
therefore reachable by 0.10 of a percentage point on the worst date — a knife edge, and precisely
the shape of bar that can only ever void.** So:

> **K1 · COVERAGE. Fires if per-date `OK` coverage falls below 85% on any rebalance date.**

**85% is chosen because the instrument clears it with more than 5pp of headroom on its worst date
and the choice is checkable against the printed distribution above.** It is not chosen to be easy:
it is chosen to be a bar this account can actually reach, so that a fired `K1` would mean the map
had genuinely degraded rather than that the bar was decorative.

**The 13.21% disagreement is the cost, and it is the arm's own quantity** — `S25` measured
**11.37%** at the NAME level; a re-ranking pays it per CELL. **It is required output, not a
defect**: without it a moved name cannot be attributed between the look-ahead being repaired and
the taxonomy being switched.

---

## 5. THE GATE — `SECTOR-NEUTRAL-B6`'s, VERBATIM

**`holdout_compare_panels`, the shipped function, unmodified.** The arm must beat the incumbent by
**BOTH** margins, in **BOTH** halves, under **BOTH** weightings, boundary embargoed:

* **long-short *t* margin > +0.25**, and
* **top-decile alpha margin > +100 bps**.

**Ambiguous against a pre-committed threshold is a NULL** (`RUN_RULES` A6). **Anything that clears
is recorded ELIGIBLE, never adopted.**

**And `SECTOR-NEUTRAL-B6`'s own failure shape is pre-named so it cannot be re-discovered as a
finding:** on the void panel sector-neutral **bought long-short *t* and sold alpha**, and the
rejection was a judgement that a long-only book should not make that trade. **If that shape recurs
here it is reported as the same trade-off and does NOT clear**, because the gate requires both
margins.

---

## 6. POWER — MB22, BOTH VOCABULARIES, PRINTED BEFORE THE VERDICT (`RUN_RULES` A-11)

**There is NO CALIBRATED FLOOR for a paired within-panel difference** — `V2G` established it and
`R1-VAR` re-confirmed it; `X7` calibrates **levels**. So the critical value used for the MDE is
**labelled UNCALIBRATED** wherever it appears, and both are reported:

* **at `crit` = 2.0** (the conventional reference `V2G` and `MB8` used), and
* **at `crit` = 3.3194543** (the honest hurdle at the post-booking `N` = 247).

`MDE_50% = crit x se` and `MDE_80% = (crit + 0.84) x se`, with `se` the **measured** paired HAC
standard error of the difference series across the 69 rebalance dates. **`se` is measured in the
controls pass and the MDE is printed BEFORE the verdict is read.** `MB8`'s rule binds and is
quoted so it cannot be forgotten: **an `se` may NOT be borrowed across perturbation sizes** — its
own 0.1106pp and `V2G`'s 0.9354pp differ 8.5-fold for that reason — so this register measures its
own and quotes no other.

**Scale, so a null is interpretable when it arrives:** `SECTOR-NEUTRAL-B6` measured this arm at
**−1.09pp** of alpha and **−0.494** of long-short *t* under deployed weights. **A verdict quoted
without its MDE is a void condition (§8).**

---

## 7. KILLS — before the arm, in their own pass (`O10`'s process defect, not repeated)

| kill | fires when | consequence |
|---|---|---|
| **K1 · COVERAGE** | per-date `OK` coverage < **85%** on any rebalance date | STOP (§4) |
| **K2 · BITE** | the PIT map changes the sector on **< 5%** of covered cells | STOP — the arm is inert and `S16`'s rank-identity lesson applies: a change that moves no grouping cannot move a ranking |
| **K3 · DEGENERACY** | any scored date has a sector group of **< 2 names**, or the number of distinct sectors on any date falls below **5** | STOP — a within-group demean on a singleton is the identity, and `SECTOR-NEUTRAL-B6` passed only because it had 11 sectors and no singletons |
| **K4 · FIDELITY** | the incumbent arm fails to reproduce the published record | STOP — `MA28`'s C1 and `MB8`'s C1 both fired in real life |
| **K5 · LOOK-AHEAD** | any cell resolves a sector from a date **after** the rebalance date | VOID — the entire point of `S25` is that the map refuses rather than carrying a classification backwards |

---

## 8. VOID CONDITIONS

1. Quoting any verdict **without its MDE** (§6).
2. Scoring **one** weighting, or **one** half, and reporting it as the result.
3. Changing the gate, the margins, the coverage bar, or the sector source after any outcome is seen.
4. Reading the arm before K1–K5 are banked and green.
5. Counting a **taxonomy revision** as a reclassification event (§2).
6. Re-opening `S15` or any other sector construction inside this register — each is its own
   hypothesis at its own price.
7. **Adopting anything.** This register measures.

---

## 9. PRIOR AND EXPECTATIONS, WRITTEN BEFORE THE RUN

**PRIOR: ~12% that the arm clears both margins in both halves under both weightings.** Built
hostile-first: **sector-neutral has been REJECTED TWICE on measurement**, the second time on a
panel that counts; the deployed run gave up **1.09pp** of alpha; and `S25`'s own repair note
records that a dated map **removes the DATA objection and does not touch the REJECTION**. The prior
is not zero because the disagreement is **13.21% of cells** — materially more than nothing — and
because a look-ahead sector is a genuine defect whose repair has never been measured on the
ranking.

**Expectations:**

1. The arm is **REJECTED** on at least one margin in at least one half — **85/15**.
2. `K2` (bite) does **not** fire, i.e. the map moves ≥ 5% of covered cells — **90/10**, given the
   13.21% disagreement already measured.
3. The **alpha** margin is the binding one rather than the *t* margin, repeating
   `SECTOR-NEUTRAL-B6`'s bought-*t*-sold-alpha shape — **65/35**.
4. The PIT arm scores **closer to the incumbent** than the today's-sector arm did, i.e. the
   look-ahead repair reduces the damage without reversing it — **60/40**.
5. At least one number here contradicts this list — **60/40**.

---

## 10. WHAT THIS REGISTER DOES NOT DO

It **adopts nothing** and touches no file under `valuation/screener`, `valuation/web` or
`valuation/engine`. It does **not** re-open `S15`, does **not** overwrite `SECTOR-NEUTRAL-B6`
(whose two rejections stand on their own terms), does **not** license the sector column for any
other use, and makes **no claim about the `max_sector_w` concentration cap**, which is an accepted
risk control and a different object. **A NULL closes the re-open condition `SECTOR-NEUTRAL-B6`
named and nothing wider** — and specifically does **not** establish that point-in-time sectors are
worthless, only that repairing this look-ahead does not rescue this ranking.
