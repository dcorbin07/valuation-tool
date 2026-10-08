# PREREG — STAGE-1 BATCH 2 — the Frontier Scout's draft, ACCEPTED WITH FIVE AMENDMENTS

**THIS IS THE REGISTER.** Committed **ALONE** — markdown only, zero `.py` — as a strict git
ancestor of every commit that computes an outcome. `RESEARCH_CHARTER.md` §3.

**EXECUTOR PASS ON `PREREG_DRAFT_stage1_batch2.md`.** The draft is accepted in substance. Five
amendments are recorded in §0, **every one of them formed before any outcome of this batch
exists** — three are the draft's own instructions carried out, one is a premise correction that
runs in the draft's favour, and one is a scope limit the draft does not state.

**`k` = 6 THROUGHOUT, WHATEVER IS RUN.** An arm that cannot be built is `NOT RUN` and `k` stays
**6**. Shrinking it after a build failure makes every surviving threshold easier, which is the
reason `STAGE1-BATCH1` held `k` = 12 with only three arms scored.

---

## 0. AMENDMENTS — all five fixed BEFORE any outcome exists

### 0.1 `B6` IS WITHDRAWN, AND THIS IS THE DRAFT'S OWN INSTRUCTION RATHER THAN MY JUDGEMENT

The draft's §8 reads: *"`B6` is withdrawn if only one junk arm is to be run — `B1` is the
pointer."* Its §6 ranks `B6` **below** `B1` deliberately and calls it *"a second junk DEFINITION,
not a second junk arm"*. One junk arm is run, and it is `B1` — `TIERED-POOL`'s own named forward
pointer, using that register's own three screens verbatim. **`B6` is `NOT RUN` and `k` stays 6.**

**AND ITS OWN KILL WOULD HAVE BEEN THE BINDING CONSTRAINT ANYWAY, which is recorded so the
withdrawal is not mistaken for a convenience.** `B6` needs eight CHS inputs including `TLMTA` and
`CASHMTA`, whose coverage on this universe the draft calls **unmeasured**, against a universe
whose worst-theme missing rate is **0.1956 even over $10B** (`POOL-SIZE`). Withdrawing it costs a
coverage census, not a verdict.

### 0.2 `B4` IS CONDITIONAL ON A TIER-LEVEL IBES CENSUS, DECLARED HERE BEFORE IT RUNS

The draft makes `B4` conditional on r1's dated IBES link existing and passing its own validation.
**It exists and it passes as an instrument** (`IBES-LINK`, landed 2026-10-07: 19 tests, 7 of 7
mutations, both routes agreeing at **0.994643** once `spans()` was keyed on `ibes_ticker` rather
than `oftic`). **Its COVERAGE is a separate question and it FAILS on the full universe.**

Measured, on the 289,659-cell corrected panel: the dated CRSP-cusip route resolves
**0.6999955119640681** of cells and **0.6904** of names against the project's inherited **0.70**
non-null floor. **ALL FOUR READINGS FAIL.**

**0.69999551 IS NOT A PASS AND IS NEVER TO BE READ AS ONE.** It misses by 4.5e-06, which is
exactly the knife edge `W-28`'s `K1` died on — a 90% bar cleared by 0.10pp — and `W-28`'s rule is
that a pre-committed bar may not be relaxed after watching it fail. A floor that bends by 4.5e-06
is not a floor.

**WHAT IS PERMITTED IS A DIFFERENT POPULATION, AND IT IS THE CHARTER'S OWN GOVERNING ONE.**
Charter Stage 1b makes **the tier govern** advancement, and the draft's own `B6` kill measures
*"Input coverage on the **TIER** (the governing population)"*. So a tier-level census is this
batch's own convention rather than a relaxation of the full-universe reading, and `O-1`'s lesson
is the reason it is a separate measurement rather than an inherited one: that item applied an
alert-book figure to the panel and was **~17× wrong**.

**`K0` — THE TIER IBES CENSUS, pre-committed in both directions.** On the build quadrant's
`cap >= $10B` tier, the dated route's `OK` share of **cells** and of **names** must BOTH reach
**0.70**. If both clear, `B4` runs. If either fails, **`B4` is `NOT RUN`**, `k` stays 6, and the
tier figure is reported beside the full-universe 0.69999551 so neither is mistaken for the other.
**No second route, no third population, and no re-reading of the full-universe figure.**

### 0.3 `B5` IS UNBLOCKED, AND ITS SIGN IS PINNED BECAUSE GETTING IT WRONG MEASURES THE OPPOSITE

The draft records `B5` as blocked on `WRDSProvider._KEEP` carrying neither `ncfdiv` nor
`ncfcommon`, and says it *"should be batched with any other arm needing new columns rather than
paying that cost alone"*. **That is exactly what happened**: `CORRECTED-REBUILD` added both (plus
`capex` and C9's four) in **one** rebuild, with coverage measured on the export first — `ncfdiv`
**0.9242**, `ncfcommon` **0.9383** non-null on the corrected universe, both clearing 0.70 — and
the three declared changes proved **additive at 3,251,787 cells with zero moved**.

**THE SIGN. Both columns are NEGATIVE for cash returned to holders**, so net payout yield is

    net_payout = -(ncfdiv + ncfcommon) / marketcap

Verified on a named row rather than assumed: AAPL 2019-06-28 reads `ncfdiv` **−3.443bn** and
`ncfcommon` **−23.312bn**, about **2.76%** of market cap for the quarter. **Getting this backwards
measures cash RAISED and inverts the arm**, which is the same family as the `capex` sign trap the
batch-3 draft records itself getting backwards on its first reading.

**AND THE NON-ZERO SHARE IS A DIFFERENT QUANTITY FROM COVERAGE, which matters for a payout
column**: zero is a legitimate value, so non-null is **coverage** and non-zero is **economic
incidence**. `ncfdiv` is non-zero on **33.55%** of corrected rows against **50.79%** restricted —
consistent with a wider universe holding smaller, younger, non-paying firms — and reading 0.3355
as coverage would understate the usable population by two thirds.

### 0.4 A PREMISE CORRECTION ON `B2`, AND IT RUNS IN THE DRAFT'S FAVOUR

The draft invokes `R1-VAR`'s standing ruling — *a Sharpe or volatility gain bought with alpha is
not worth having unless the Sharpe itself is bad* — and states *"the book runs **Sharpe 0.5866**
at an IR of about 0.88/yr, so the antecedent does not fire."*

**0.5866 is the RESEARCH DECILE BOOK'S Sharpe, not the Index book's.** `B2`'s overlay is applied
to the **Index book**, whose own net Sharpe is **1.0318** published and **0.9694** on the
corrected universe (`INDEX-BOOK-3WAY`). **The amendment strengthens the draft's own conclusion**:
at a Sharpe near **1.0** the antecedent fires even less than at 0.59, so **an improvement in
Sharpe or realised volatility alone is even further from being a pass.** The draft's verdict rule
is adopted unchanged; only the number it cites is corrected, and it is corrected against the arm's
own object.

### 0.5 `B1` AND `B2` CANNOT MEET DON'S RULE AT STAGE 1, AND THE DRAFT DOES NOT SAY SO

Both are construction changes judged on **Don's rule**: beat the incumbent on net Roth return
**and** not be worse on drawdown by more than 3pp, **on 2009–2026 AND on the 1999–2008 five-theme
proxy**, each against that period's own incumbent.

**STAGE 1 IS THE BUILD QUADRANT ONLY** — 2009–2019 × `stable_key_half(ticker) == 0` — so **neither
the 2020–2026 remainder nor the 1999–2008 proxy is available here.** Reading either would spend a
Stage-2 or Stage-3 look that cannot be replaced.

**SO NEITHER `B1` NOR `B2` CAN *PASS* DON'S RULE AT STAGE 1, BY CONSTRUCTION.** What they can do
is fail it, or clear its margins on the evidence Stage 1 holds. Pre-committed here:

* They are judged on **Don's own margins** — net Roth return above the incumbent's, drawdown no
  worse than 3pp — applied to **BOTH HALVES of the build quadrant** (the charter's Stage-1a split,
  **24 / 20** dates at 2014-12-31, both clearing `min_dates` = 16).
* An arm clearing both halves is recorded **`STAGE-1 PASS, 1999-2008 LEG NOT RUN`**, and **that
  label may NOT be read as meeting Don's rule.** It means the arm is worth a Stage-2 look and
  nothing more.
* An arm failing either half is **REJECTED** and does not advance. A failure needs no 1999–2008
  leg, because Don's rule is a conjunction.

---

## 1. THE BATCH — five arms, membership fixed here, `k` = 6

| arm | what | judged on | in the BH set? |
|---|---|---|---|
| **B1** | `TIERED-POOL`'s three junk screens, on the incumbent's own $10B tier | Don's margins, both build-quadrant halves | no — construction change |
| **B2** | volatility-managed exposure on the Index book, `min(1, c/σ²)` | Don's margins, both halves | no — construction change |
| **B3** | Blitz-Huij-Martens residual momentum, 36-month formation | incremental IC vs the deployed composite | **yes** |
| **B4** | analyst neglect (`numest` scaled by size) | incremental IC | **yes, IF `K0` clears** |
| **B5** | net payout yield | incremental IC | **yes** |
| ~~B6~~ | ~~CHS distress probability~~ | — | **WITHDRAWN (§0.1)** |

**Benjamini-Hochberg at q = 0.10 across `k` = 6**, the *i*-th smallest *p* against *i*·0.10/6:

| i | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| threshold | .01667 | .03333 | .05000 | .06667 | .08333 | .10000 |

**B1, B2 and B6 are OUTSIDE the BH set** and the draft's reason is adopted: §6 forbids inventing a
*p* so that a method applies. B1 and B2 are preference rules on point estimates; B6 is not run.
**All five are still COUNTED in the research log**, so all five raise the HLZ hurdle and the
Deflated Sharpe denominator.

---

## 2. TRIALS — 5 equity, booked BEFORE any runner exists

Five arms, one trial each, **booked in their own commit before any arm code is written**. Equity
`N` **274 → 279**. B6 charges nothing because it is not run; `K0` charges nothing because a
pre-outcome control can only BLOCK (`MB1-SEL`).

---

## 3. THE PANEL, THE QUADRANT AND THE STATISTIC

* **PANEL: `UNIVERSE_BIAS_PANEL_full_v3.pkl`** — the rebuilt corrected panel, 289,659 × 90, all
  seven weighted themes LIVE, `keep_numbers=True`, S22's full horizon grid. It is the panel `B3`
  and `B5` need columns from, and it is **proved additive** over the lean panel at 3,251,787 cells
  with zero moved, so every floor `CORRECTED-FLOORS` calibrated still describes it.
  **Never `data/backtest`.**
* **QUADRANT: 2009–2019 × `stable_key_half(ticker) == 0`** — `X1`'s `sha1(ticker) % 2`, CALLED from
  `scripts/r4_x1_accounting_universe.py` and never re-implemented (`B7`).
* **STATISTIC (charter Stage 1a): the incremental control is the DEPLOYED COMPOSITE**, one column
  from `composite_from_frame` (called, never re-implemented), z-scored within date — **not**
  complete-case residualisation on seven themes, which left `STAGE1-BATCH1` a **five-date** early
  half. All **44** build-quadrant dates survive; halves **24 / 20** at 2014-12-31.
* **POPULATION (charter Stage 1b): BOTH, AND THE TIER GOVERNS.** Full corrected universe answers
  *is it real?*; the incumbent's own `cap >= $10B` tier answers *is it any use?* An arm passing
  wide and failing the tier is **`REAL BUT NOT INVESTABLE HERE`** and does not reach Stage 2. The
  tier ships its **per-date name count** and must clear `CONTRACT_MIN_POSITIONS` = **50** on every
  date, or the arm is `NOT ASSESSABLE` on the governing population.
* **EVERY CRITICAL VALUE IS LABELLED UNCALIBRATED.** No bar calibrated on the 2,531-name panel
  transfers: this universe's own deployed headline is **+6.07%** top-decile alpha, and
  `CORRECTED-FLOORS` measured its own floors on it.

---

## 4. THE ARMS, THEIR CONSTRUCTIONS AND THEIR FREE PRE-OUTCOME KILLS

**ALL KILLS RUN IN THEIR OWN PASS AND ARE READ BEFORE ANY ARM IS SCORED** (`O10`: a gating control
computed in the same pass as the outcomes cannot be claimed to have been read first). The arm
runner **REFUSES** without a passing kill artifact.

### 4.1 `B1` — the junk filter on the incumbent's own $10B tier

`TIERED-POOL`'s own three screens, reused verbatim rather than re-chosen
(Asness-Frazzini-Israel-Moskowitz-Pedersen 2018). A tier name must satisfy all three:

1. positive TTM net income — `_ttm(rows, as_of, ("netinc",)) > 0`
2. positive TTM free cash flow — `_ttm(rows, as_of, ("fcf",)) > 0`
3. `debt / equity` not in the worst third of its date's cross-section, from `fundamentals_pit`

**`_ttm` IS CALLED, NEVER RE-IMPLEMENTED (`B7`)**, and it matters for more than tidiness: it
collapses restatements (`D10-a` — 3.15% of `(ticker, reportperiod)` groups carry more than one
`datekey`), requires four distinct quarters, and refuses a window spanning more than
`TTM_MAX_SPAN_DAYS`. **A hand-rolled sum would silently understate a flow and read as a junk
company — the direction that would flatter this arm.**

**`K1` — INERTNESS, and the draft calls it the likeliest of the six to fire.** The tier is already
large-cap and may already be clean: `TIERED-POOL` measured **0.0%** of incumbent weight below
$300M. So the kill measures the **share of tier names failing at least one screen, per date**, and
the arm is **`INERT`, carrying no verdict, if the median is < 2%.** A filter that removes nothing
cannot move a book, and reporting a near-zero change as a null would be a statement about the book
rather than about junk. **Second bound in the same kill:** the filtered tier must still clear
**50** names on every date, and the per-date count ships.

### 4.2 `B2` — volatility-managed exposure on the Index book (Moreira-Muir 2017)

`w_t = min(1, c / σ²_{t-1}) · w_base`, with `σ²` from **daily** returns of the Index book inside
the prior rebalance window and `c` set so **average exposure over the build quadrant is 1.0** — a
normalisation declared before any look, so the arm is not a disguised bet on holding less.

**THE `min(1, ·)` CAP IS A DECLARED DEVIATION FROM THE PAPER AND THE REASON IS THE PRODUCT.** The
paper levers **up** when volatility is low; this is a Roth with no margin, so exposure above 100%
is unavailable and an uncapped overlay would measure a strategy the account cannot run. Capped, it
is *"de-risk in high volatility, never lever up"* — **weaker than the paper's, and honest about
it.**

**`K1` — THE LEVERAGE CENSUS, and it decides whether the arm is even the paper's strategy.** The
share of build-quadrant dates on which the **uncapped** `c / σ²_{t-1}` exceeds 1.0. If that share
is **> 0.50**, the paper's effect is majority-carried by leverage the account cannot take, and the
arm is recorded **`NOT THE PAPER'S STRATEGY`** — run only as the capped de-risking overlay it
actually is, with that label on every figure. No outcome is touched: this is a census of a scaling
factor.

**`R1-VAR` GOVERNS AND §0.4 CORRECTS THE NUMBER IT CITES.** An improvement in Sharpe or realised
volatility **alone is NOT a pass.** The Index book's own net Sharpe is **1.0318** published,
**0.9694** corrected — not bad — so `R1-VAR`'s antecedent does not fire.

**THE LITERATURE'S COUNTER-EVIDENCE IS PRE-COMMITTED AS A PRIOR.** Cederburg, O'Doherty, Wang and
Yan (2020) find volatility management **fails out of sample for most factors** and that its gains
**concentrate in the market factor**. The Index book is not the market factor, so **the prior here
is unfavourable and a null is the expected outcome rather than a disappointment.**

### 4.3 `B3` — Blitz-Huij-Martens residual momentum

36-month formation window; residual of each name's monthly return on the **panel's OWN
value-weighted market return**, built from the panel's prices; signal is the *t*-scaled cumulative
residual with the most recent month skipped.

**DELIBERATELY A ONE-FACTOR RESIDUAL, declared as a deviation from the paper's three**, and the
reason is licensing rather than convenience: Ken French's library is *"free but permission-gated
and factor-level — never a magnitude claim"* (`RUN_RULES` 0.2), so a signal whose construction
depends on French factors could validate a build and **could never ship in a product figure**.
**French is used nowhere in this arm.**

**`K1` — THE COSTUME BAR, AND THE SIGNAL IS BUILT INSIDE THE KILL PASS.** Batch 1's `A2b` was NOT
RUN because its costume bar *"cannot be evaluated before the SIGNAL exists"* — an ordering problem,
not an outcome. The signal column is built **inside the kill pass**, where no forward return is
touched, and the bar is then evaluated on it: mean per-date |ρ| against the shipped `momentum`
theme must be **< 0.60**. **And if it lands above 0.50, a pass is read residualised on `momentum`
alone** — the reading that killed batch 1's `A11` at 0.7596. **Fixing that reading in advance is
what stops a pass being chosen after seeing which one clears.**

### 4.4 `B4` — analyst neglect — CONDITIONAL on `K0` (§0.2)

Low analyst coverage as a standalone standardised column: `numest` from IBES `statsum`, joined on
the dated `ibes_id` link, scaled by firm size so it is coverage *relative to what a name of that
size usually attracts* rather than a size proxy.

**`K0` — the tier IBES census of §0.2.** Both cells and names must reach **0.70** on the build
quadrant's $10B tier, or `B4` is `NOT RUN` and `k` stays 6.

**`K1` — THE COSTUME BAR THAT WAS NEVER RUN.** Mean per-date |ρ| against the **`size`** theme, bar
**0.60**. **A neglect proxy is a size proxy until measured otherwise**, and the record is
unambiguous about the direction: `E-1`'s graveyard aggregate died at **0.6114** against `size`, and
`R6`'s conviction signals read **−0.815 to −0.854**. **This is the kill most likely to fire of the
three IC arms.**

### 4.5 `B5` — net payout yield (Boudoukh-Michaely-Richardson-Roberts 2007)

`-(ncfdiv + ncfcommon) / marketcap` from `fundamentals_pit`, on the argument that repurchases
substituted for dividends so dividend yield alone measures a shrinking share of what is returned.
**The sign is pinned in §0.3 and verified on a named row.**

**`K1` — NON-IDENTITY AGAINST THE SHIPPED SIGNAL, BY MEASUREMENT.** `capital_discipline` is
`neg_issuance`, derived in `_yoy()` from `sharesbas` year-over-year. **`S16` measured that
splitting net issuance into buyback and dilution legs is a RANK IDENTITY — within-date rank
correlation `1.000000000000` on all 69 dates — because `max(0, −net)` and `−max(0, net)` are both
non-increasing in `net`.** Net payout yield is **not** that identity (it adds dividends and
rescales by market cap), **but the register must PROVE non-identity rather than assume it from the
construction**: within-date rank correlation against `z_neg_issuance` must be **< 0.99**, or the
arm is the shipped signal rescaled and carries no verdict.

---

## 5. THE VERDICT RULES, fixed here

* **IC ARMS (`B3`, `B4`, `B5`)**: incremental IC *t* against the deployed composite, on **both
  halves** of the build quadrant, sign-stable, at a conventional **|t| ≥ 2.0 LABELLED
  UNCALIBRATED**; then **Benjamini-Hochberg at q = 0.10 across `k` = 6**. An arm clearing BH and
  failing the both-halves requirement is **`NOT_REPLICATED`**, which is what happened to batch 1's
  `A11` and is not a pass.
* **CONSTRUCTION ARMS (`B1`, `B2`)**: Don's margins on both build-quadrant halves, per §0.5, with
  a clearing arm labelled **`STAGE-1 PASS, 1999-2008 LEG NOT RUN`**.
* **EVERY ARM IS SCORED ON BOTH POPULATIONS AND THE TIER GOVERNS.** Wide pass + tier fail =
  **`REAL BUT NOT INVESTABLE HERE`**, no Stage 2.
* **AMBIGUOUS AGAINST A PRE-COMMITTED THRESHOLD IS A NULL** (`RUN_RULES` A6), never a judgement.
* **EVERY VERDICT TRAVELS WITH ITS MDE** (`MB8`: never borrow an `se`; `RUN_RULES` PART A rule 11),
  measured on the arm's own rows at **80% power**, and a null states what it could have seen.

---

## 6. VOID CONDITIONS

1. **No grid.** Each arm has ONE construction. No burn-in sweep, no window sweep, no threshold
   sweep. Choosing a parameter after seeing a verdict voids the arm.
2. **No Stage-2 or Stage-3 look.** The check quadrant stays closed; the 2020–2026 remainder and the
   1999–2008 proxy are not read. Looking at either to choose among these arms spends a look that
   cannot be replaced.
3. **`k` STAYS 6** whatever is run.
4. **Quoting a subset of the populations is a void condition.** Both the full universe and the tier
   are reported for every scored arm, whichever way they disagree.
5. **No bar may be relaxed after it fires** (`W-28`). `K0`'s 0.70, `K1`'s 0.60 and 0.99, B1's 2%
   and 50-name floors, B2's 0.50 leverage share: all fixed here.
6. **0.69999551 may not be read as clearing 0.70** in any report, summary or successor.
7. **Nothing is adopted.** Adoption is Don's, is a vintage event, and quotes the expected return at
   **half** the backtested size (McLean-Pontiff).

---

## 7. EXPECTATIONS, stated before the run so they can be scored

1. **`B1`'s `K1` fires `INERT`** — 60/40. The tier is large-cap and `TIERED-POOL` measured 0.0% of
   incumbent weight below $300M.
2. **`B4` is `NOT RUN` on `K0`** — 70/30. The full-universe route misses by 4.5e-06 and the tier is
   a smaller, better-covered population, so it could clear; but 0.70 is a hard floor and the
   dated-route `UNMAPPED` share is 12.9% of cells before any tier restriction.
3. **`B3`'s `K1` lands between 0.50 and 0.60** — 55/45, so a pass would be read residualised on
   `momentum` alone. Residual momentum is constructed to be orthogonal to the market, not to a
   momentum theme.
4. **`B5` clears its non-identity bar comfortably** — 80/20. It adds dividends and rescales by
   market cap, so a rank correlation near 1.0 against `neg_issuance` would be surprising.
5. **No IC arm clears BH and both halves** — 75/25. Five registers motivated by orthogonality have
   confirmed orthogonality and not one cleared.
6. **`B2` is a null, and the literature's prior is why** — 70/30.

---

## 8. WHAT THIS REGISTER DOES NOT DO

* **No arm is run and no outcome is computed here.** This file is markdown only and is committed
  ALONE, before the trials are booked and before any runner exists.
* **`B6` is NOT RUN** (§0.1) and carries no verdict in either direction.
* **`B4` may be NOT RUN** on `K0` (§0.2), and `k` stays 6 either way.
* **`A1`, `A3`, `A6`, `A7`, `A10` and `A11` do not return.** The draft's §7 gives each a reason and
  they are adopted: `A11`, `A3` and `A7` died on their own OUTCOMES; `A1`'s coverage kill fired at
  **0.6087** and re-running it at a shorter burn-in would be choosing the parameter on the outcome;
  `A6` and `A10` have no owned-data coverage fix, and `A6` cannot advance under Stage 1b anyway.
* **The 1972–1998 WRDS era stays closed** — `OOS1`'s Gate B reads **0.837303** against its
  pre-committed **0.90**.
* **Nothing is adopted, no public page changes, and no banked panel is overwritten.**
