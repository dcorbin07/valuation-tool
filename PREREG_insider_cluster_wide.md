# PRE-REGISTRATION — `INSIDER-WIDE` — the one check-quadrant read, on a wider governing tier

**Committed ALONE, markdown only, zero `.py`, BEFORE ANY CHECK-QUADRANT ROW IS READ.** A strict git
ancestor of every commit that computes a check-quadrant outcome. If it is not, the item is VOID.

Don's ruling, `DECISIONS.md` 2026-10-13: *"CLUSTERED INSIDER BUYING GOES TO A WIDER-TIER TEST… A
new register with a wider tier governing and realistic size-tiered trading costs is written BEFORE
the one check-quadrant read, and that read is taken once."*

**STAGE 1 IS `INSIDER-CLUSTER`** — `PREREG_insider_cluster.md` (`fd87870`), Amendment 1
(`826d0b5`), arm (`4db197a`). It cleared every clause on the full corrected universe in the BUILD
quadrant at `h`=63 (**+2.0926pp** market-adjusted, **+1.8077pp** over its null mean, *t* 5.009 /
4.888) while its governing `$10B` tier was underpowered by construction, so it stopped and **the
check quadrant is unspent.**

**THE CHECK QUADRANT GETS ONE READ AND THERE IS NO SECOND ONE.** Everything below is fixed now.

---

## 1. WHAT IS UNCHANGED FROM STAGE 1 — all of it, and nothing is re-chosen

* **The cluster definition**, verbatim: `k = 2` or more **DISTINCT** `ownername` filing an
  **OPPORTUNISTIC** open-market purchase (`transactioncode == "P"`, a missing code **COUNTED AND
  SKIPPED**) in one ticker inside a **30-calendar-day** window, dated at the **LAST** filing, one
  event per cluster (full-window cooldown), with the **STRICT** condition that the insider pair
  traded in **each of the two prior calendar years**. `valuation/studies/insider_cluster.py`,
  unmodified.
* **The MARKET-ADJUSTED leg ONLY.** The own-normal leg **stays out**, and the reason is this
  lane's own measurement rather than a preference: `ar_own = fwd − h × mu` subtracts the trailing
  mean daily return, insiders buy **after declines**, so a negative trailing drift is extrapolated
  forward for a quarter — it read **+11.46pp** at `h`=63 against the market leg's +2.09pp, with its
  own permutation null centred at **+1.17pp** rather than zero. **A leg whose null is not centred
  on zero is a biased benchmark, measured.**
* **The within-date permutation null**, 500 draws, event flag shuffled across names within each
  event date.
* **BOTH halves**, same sign, each clearing its own null.
* **BOTH clusterings** — event **DATE** and **TICKER** — clearing required under both.
* **Benjamini-Hochberg** across the cells read in this pass.
* **Terminal vs censored**: a delisted name keeps its terminal value; an administrative end of
  data is dropped (`E-5`).

**Nothing in the construction is touched. The ONLY new things are the governing population, the
cost treatment, and the fact that this reads the CHECK cell.**

---

## 2. THE GOVERNING POPULATION — `cap ≥ $500M`, and the principle is stated before the numbers

**THE BUILD QUADRANT IS WHERE A DESIGN IS CHOSEN** (`RESEARCH_CHARTER` §4: the build cell is
deliberately reused, *"which is the whole point of a cheap screen"*), so the tier is chosen from
build-quadrant results. **Those results are below in full, including the ones that argue against
the choice**, so a reader can see the tier was not picked by maximising anything.

### 2a. The build quadrant by DISJOINT cap band — `h`=63, market-adjusted

| band | events | tickers | gross | *t* (date/ticker) | round-trip cost | **NET** |
|---|---|---|---|---|---|---|
| `$10B+` | 141 | 78 | +3.0138pp | 2.58 / 2.51 | 0.186pp | **+2.83pp** |
| `$2B–$10B` | 470 | 238 | **−0.6869pp** | −0.94 / −0.90 | 0.400pp | **−1.09pp** |
| `$500M–$2B` | 767 | 337 | +1.9004pp | 2.23 / 2.51 | 0.800pp | **+1.10pp** |
| `$100M–$500M` | 1,354 | 495 | +2.0188pp | 3.19 / 2.96 | 1.600pp | **+0.42pp** |
| `< $100M` | 845 | 316 | +1.8557pp | 1.68 / 1.59 | 3.000pp | **−1.14pp** |

**THE GROSS EFFECT IS ROUGHLY +1.9pp IN EVERY BAND EXCEPT TWO**, and the two exceptions are the
finding: `$10B+` is **larger** (+3.01pp) and **`$2B–$10B` is NEGATIVE** (−0.69pp at *t* −0.94,
which is noise-consistent but is certainly not +1.9pp). **So the effect is NOT monotone in size and
a successor must not model it as such.** It is also why the cumulative-floor table is unreadable on
its own: a `$500M` floor contains the dead `$2B–$10B` band, which drags its cumulative figure from
the band's +1.90pp down to +1.13pp.

**AND COST, NOT SIGNAL, IS WHAT DECIDES THE FLOOR: the round trip roughly DOUBLES at each rung
down while the gross effect stays flat.** Net of cost only `$10B+` and `$500M–$2B` are clearly
positive; `$100M–$500M` nets +0.42pp with cost at **79%** of gross; and **`< $100M` is NEGATIVE at
−1.14pp**, because the cost model charges 150 bps one-way there.

### 2b. Why `$500M` governs

1. **Don's ruling is the widest pool *if the evidence holds*, and liquidity is not a constraint for
   a personal Roth — but *"the costs must be real"*.** `$500M` is **20× wider in cap than stage 1's
   `$10B`** and carries **1,120 check events against 151**.
2. **It is the lowest rung at which the round-trip cost stays below half the gross band effect**
   (0.800 against 1.900pp, 42%). The next rung down is 79% and the one below that is **over 100%**.
3. **It does not rest a governing verdict on the rung the cost model itself disclaims.** That
   model's own comment flags `< $100M` as *"often untradeable in size at all"*, and a verdict about
   tradability should not depend on the band its own cost input is least confident about.
4. **It was not chosen by maximising.** `$100M` and the full universe both have **higher** gross
   effects and **far more** check power on the gross leg (87.2% and 97.5% against 42.4%); `$10B+`
   has a higher net effect. The floor is picked on cost realism, not on any cell's size.

### 2c. Declared and read in the SAME pass, with BH across them

**One pass over the check cell is ONE read of that cell.** The charter rations the *cell*, and
forbids *"looking at the check cell to choose among constructions"* — these populations are all
declared **here, before the read**, exactly as stage 1 declared two, so nothing is chosen
afterwards.

| cell | role |
|---|---|
| **`cap ≥ $500M`** | **GOVERNS.** Advancement rests on it. |
| the **FULL** corrected universe | **VERDICT-CARRYING.** The cell that can resolve the GROSS phenomenon (power 97.5%). |
| **`cap ≥ $10B`** | **VERDICT-CARRYING.** The cell that can resolve the NET economics (power 67.0%), and stage 1's own unresolved tier. |
| `cap ≥ $2B`, `cap ≥ $100M` | **NO VERDICT.** Reported so the tier curve ships whole. |

**`h` = 63 GOVERNS. `h` = 126 IS REPORTED ONLY** and carries no verdict — stage 1 found it NULL on
its early half, and promoting it now, after seeing that, would be choosing the horizon on an
outcome.

---

## 3. COSTS — size-tiered, per event, from this project's own model

**`fundamental_panel.one_way_cost_bps`, CALLED and never re-implemented** (`B7`), charged at the
name's **point-in-time** market cap, round trip = **2×** one-way:

| cap | one-way | round trip |
|---|---|---|
| ≥ $200B | 4.0 bps | 0.08pp |
| ≥ $50B | 6.0 | 0.12pp |
| ≥ $10B | 10.0 | 0.20pp |
| ≥ $2B | 20.0 | 0.40pp |
| ≥ $500M | 40.0 | 0.80pp |
| ≥ $100M | 80.0 | 1.60pp |
| < $100M | 150.0 | 3.00pp |

**STAGE 1'S 0.67pp FLOOR IS SUPERSEDED HERE AND THE CORRECTION IS WORTH STATING.** That figure is
`2 × B11`'s **33.4 bps**, which is the *realised, book-weighted* one-way cost of the top-decile
book — **one average over a megacap-tilted book**, not a cost for the name in front of you. Applied
to a `< $100M` name it understates by **4.5×**; applied to a megacap it overstates by **8×**. The
event-weighted round trip for the governing tier is **0.601pp** and for the full universe
**1.723pp**, and **each event is charged its own.**

**THE MODEL'S OWN CAVEAT TRAVELS WITH IT**, verbatim: *"deliberately round, conservative-side
numbers rather than a fitted microstructure model."* It is **half-spread plus market impact**.
**A SPREAD-ONLY VARIANT IS DELIBERATELY NOT CONSTRUCTED**, even though Don's ruling that liquidity
is not a constraint for a personal Roth would justify a smaller impact term: **this project owns no
equity spread data, so a spread-only figure would be an invented number, and inventing a cheaper
cost model to help a result pass is the flattering direction.** The consequence is stated plainly:
**the cost charged here is an upper bound for a personal-sized account, so a net result that clears
it clears comfortably, and a net result that fails it may still be tradeable at personal size.**
That asymmetry is declared now, not after.

---

## 4. THE BARS — all five, any other outcome a NULL

* **A1 — SIGN.** The market-adjusted mean is POSITIVE.
* **A2 — ITS OWN NULL.** It exceeds that cell's own within-date permutation p95 on the full check
  sample **and in both halves** (boundary **2023-01-01**, declared here), same sign throughout.
* **A3 — INFERENCE.** Cluster-robust *t* > **2.0** on the event DATE **and** on the TICKER.
  **LABELLED UNCALIBRATED** (`V2G`, `R1-VAR`); the HLZ hurdle at the then-current equity `N` is
  **reported beside and NOT gated**, derived from `statistics.hlz_hurdle`.
* **A4 — ECONOMIC, AND THIS IS THE CLAUSE DON'S RULING ADDS.** The mean must exceed the cell's own
  **event-weighted size-tiered round-trip cost** from §3. Stage 1's single 0.67pp floor is not used.
* **A5 — BENJAMINI-HOCHBERG at q = 0.10, `k = 3` FIXED HERE AND NEVER SHRUNK** across the three
  verdict-carrying cells. The two no-verdict cells are excluded **with the exclusion declared
  here**.

**THREE STATES, `P1S0`'s grammar, and the third is why this register can be honest:
CONFIRMED / NOT CONFIRMED / UNDERPOWERED.** A cell whose pre-declared power against the build
effect is below 50% returns **UNDERPOWERED** rather than NOT CONFIRMED, because at that power a
null is *"invisible at this resolution"* and reporting it as absence would be false.

---

## 5. POWER — stated for every cell BEFORE the read, and one leg is declared unanswerable

From the **BUILD cell's own REALISED cluster-robust `se`** scaled by `sqrt(n_build / n_check)` —
an estimate on this construction's own measured `se` (`MB8`), not the `sqrt(n/G)` worst-case bound.
**`BETA-FORECAST` measured how far that bound lands from reality: it predicted an MDE80 of 0.0548
and the realised figure was 0.0094, about 6× better.** Both are banked in
`data/free_analysis/INSIDER_WIDE_TIER_CHOICE.json`; the realised scaling is the figure quoted.

| cell | check n | `se` | MDE80 | GROSS effect | **power, GROSS** | NET effect | expected *t*, NET | **power, NET** |
|---|---|---|---|---|---|---|---|---|
| **`$500M` (GOVERNS)** | 1,120 | 0.626pp | 1.778pp | +1.132pp | **42.4%** | +0.531pp | +0.85 | **12.7%** |
| FULL universe | 2,669 | 0.529pp | 1.503pp | +2.093pp | **97.5%** | +0.370pp | +0.70 | **10.0%** |
| `$10B` | 151 | 1.159pp | 3.292pp | +3.014pp | **72.6%** | +2.828pp | +2.44 | **67.0%** |
| `$2B` (no verdict) | 540 | 0.694pp | 1.972pp | +0.167pp | 5.2% | −0.183pp | −0.26 | 0% |
| `$100M` (no verdict) | 2,020 | 0.501pp | 1.424pp | +1.571pp | 87.2% | +0.476pp | +0.95 | 14.8% |

**THE HONEST STATEMENT, AND IT IS SAID BEFORE THE READ RATHER THAN AFTER:**

1. **The GOVERNING cell's gross leg is powered at 42.4% — below half.** So **`cap ≥ $500M` is
   pre-declared to return UNDERPOWERED on a null**, and only a *positive* result there is
   informative. That is a real limitation of a tier chosen on cost realism rather than on power.
2. **The NET-OF-COST question is UNANSWERABLE AT EVERY WIDE TIER** — 10% to 15% power, expected *t*
   of 0.70 to 0.95. **A net null at any wide tier is invisible, not absent**, and may not be
   reported as evidence the strategy does not pay.
3. **ONLY TWO CELLS CAN RESOLVE ANYTHING.** The **full universe** can confirm the GROSS phenomenon
   (97.5%); **`$10B+`** can resolve the NET economics (67.0%). **Those two are why this read is
   worth taking at all**, and they are declared as verdict-carrying for exactly that reason.

**AND A CORRECTION TO STAGE 1'S OWN FRAMING, MADE HERE BEFORE THE READ.** Stage 1 declared the
`$10B` tier `UNDERPOWERED-BY-CONSTRUCTION` at **7.4%**, computed against the *literature's*
hypothesised 1.23pp. The build quadrant then **measured +3.01pp** in that tier, and against its own
measured effect the check read has **67.0%** net power. **Both statements are right and they are
not the same statement:** a Stage-1 screen cannot power against an effect it has not yet measured
without circularity, while a Stage-2 confirmation's correct target *is* the measured build effect.
**So stage 1's label stands as written and `$10B+` is nevertheless the best-powered economic cell
here** — which is why it is read rather than dropped.

---

## 6. Trials

**THREE EQUITY TRIALS**, booked **BEFORE any runner for this item exists** — one per
verdict-carrying cell (`$500M`, full, `$10B`). The two no-verdict cells and `h`=126 are **not
charged**; they are declared here so none can be promoted after the fact. Charged to **equity**;
overstating is the safe direction (`MA6`).

---

## 7. FREE PRE-READ CHECKS — their own pass, before any check-quadrant outcome

The read runner **REFUSES** without a passing artifact (`O10`: a gating control and its outcomes
must not run in one pass).

* **C1 — THE CONSTRUCTION IS BIT-IDENTICAL TO STAGE 1'S.** Re-deriving stage 1's own build-quadrant
  `h`=63 full-universe figures from this item's code must reproduce **+2.0926pp**, *t* **5.009 /
  4.888** and **4,072** events **exactly**. If the instrument has drifted, the comparison the whole
  item rests on is between two different things, and the read does not happen.
* **C2 — NO CHECK-QUADRANT OUTCOME HAS BEEN READ YET.** No artifact under `data/free_analysis/`
  may contain a check-quadrant abnormal return before the read pass runs, and
  `tests/test_insider_wide.py` asserts the tier-choice module computes none, over the syntax tree.
* **C3 — THE COST MODEL IS THE SHIPPED ONE.** `one_way_cost_bps` is imported and the table is not
  retyped, pinned by test.
* **C4 — THE CHECK CELL IS THE RIGHT CELL**: era `check`, ticker half **1**, disjoint from the
  build cell by construction, with its event count matching the census's independently banked
  **2,669**.

---

## 8. Void conditions

1. **The check quadrant read more than once**, or read before this register is committed, or the
   cell definitions changed after any check figure is seen.
2. **The governing tier changed after the read**, or a no-verdict cell promoted to a verdict.
3. **`h` = 126 given a verdict.**
4. **Stage 1's 0.67pp floor substituted for the size-tiered cost**, or a cheaper cost model
   invented (§3).
5. **The own-normal leg quoted anywhere as a result.**
6. **A null reported as absence in a cell this register has already declared UNDERPOWERED** (§5).
7. **A floor borrowed** from X7 or `CORRECTED-FLOORS`.
8. **Anything adopted.** If it confirms, the next rung is a **forward paper book in shares**, which
   is **Don's decision** and not this lane's.

---

## 9. Expectations, stated now

1. **The FULL universe's gross leg CONFIRMS**, at 65/35 — it is the one well-powered cell and the
   build effect is large.
2. **The GOVERNING `$500M` cell returns UNDERPOWERED rather than CONFIRMED**, at 55/45.
3. **No cell clears A4 (the size-tiered cost) except `$10B+`**, at 70/30.
4. **`$10B+` confirms net of cost**, at 50/50 — a genuine coin flip, and the most interesting cell.
5. **At least one cell's halves disagree in sign**, at 60/40.
6. **The `$2B–$10B` dead band reappears in the check quadrant**, at 40/60 — if it does, it is a
   structural fact about that cap range; if it does not, it was noise in the build cell.

---

## 10. Not done

* **Nothing is adopted**, no forward book is declared, and no public surface changes.
* **Stage 3 (the pre-2009 eras) is untouched and remains foreclosed** for this construction — the
  strict definition leaves **31** events before 2009.
* **No `k = 3`, no broad opportunistic label, no sell-side arm, no size-weighted cluster.**
* **No spread-only cost variant** (§3) and **no change to `one_way_cost_bps`.**
* **Stage 1's register and verdict are not edited.** Its `$10B` UNDERPOWERED label stands as
  written, for the reason §5 gives.
