# PREREG DRAFT — STAGE-1 BATCH 2 — six arms, under the repaired template

**A DRAFT AND NOT A REGISTER. ZERO TRIALS.** No arm is run, no outcome statistic is computed, no
trial is booked, and nothing is measured here. A register is committed **ALONE** (markdown only,
zero `.py`, a strict git ancestor of every measurement commit) — `RESEARCH_CHARTER.md` §3.

**It is drafted under the template as REPAIRED on 2026-10-07** — charter §5 **Stage 1a** (the
statistic) and **Stage 1b** (the population), both fixed before this draft existed. Batch 1's
binding result was methodological, not empirical, and that repair is the precondition for this
batch meaning anything.

---

## 0. WHAT THE REPAIR CHANGES FOR EVERY ARM BELOW

* **The incremental control is the DEPLOYED COMPOSITE**, one column from `composite_from_frame`
  (called, never re-implemented), z-scored within date — **not** complete-case residualisation on
  seven themes. All **44** build-quadrant dates survive, halves **24 / 20** at 2014-12-31, both
  clear `min_dates` = 16, so **a both-halves verdict is assessable**, which it was not in batch 1.
* **Every arm is scored on BOTH populations and the TIER GOVERNS.** Full corrected universe
  answers *is it real?*; the incumbent's own `cap >= $10B` tier answers *is it any use?* An arm
  passing wide and failing the tier is `REAL BUT NOT INVESTABLE HERE` and does **not** reach
  Stage 2.
* **Costume kills stay where they were** — mean per-date |ρ| against **each** theme at **0.60**,
  in the kill pass, before any forward return is touched.
* **No bar calibrated on the 2,531-name panel transfers**: this universe's own headline alpha is
  **2.83% at HAC *t* 1.08**, so every critical value is **LABELLED UNCALIBRATED**.

### 0a. THE BATCH IS SIX ARMS, MEMBERSHIP FIXED HERE

**Benjamini-Hochberg at q = 0.10 across `k` = 6**, the *i*-th smallest *p* against *i* · 0.10 / 6:

| i | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| threshold | .01667 | .03333 | .05000 | .06667 | .08333 | .10000 |

**An arm that cannot be built is NOT RUN and `k` STAYS 6** — shrinking it after a build failure
makes every surviving threshold easier. Batch 1 held `k` = 12 with only three arms scored for
exactly this reason.

**AND THREE OF THE SIX ARE OUTSIDE THE BH SET, DECLARED HERE** (§6 forbids inventing a *p* so a
method applies):

* **IN THE BH SET** — the incremental-IC arms: **B3, B4, B5**.
* **EXCLUDED, JUDGED ON A PRE-COMMITTED MARGIN** — **B1** and **B2** are **construction changes**
  judged on **Don's rule** (net Roth return **and** drawdown, **both periods**), which is a
  **preference** rule deciding on point estimates by design; and **B6** is a filter gated on a
  crash-rate ratio. All three are still **counted** in the research log, so all three raise the
  HLZ hurdle and the Deflated Sharpe denominator.

---

## 1. B1 — THE JUNK FILTER ON THE INCUMBENT'S OWN $10B TIER *(TIERED-POOL's one forward pointer)*

**WHY IT IS GENUINELY UN-RUN AND NOT A RE-RUN.** `TIERED-POOL`'s arm B applied its junk filter
**only to the two bands below $10B** — its register says so in terms: *"The filter applies to the
two bands below $10B only; the `>= $10B` band is arm A's unchanged."* **So the filter has never
touched the incumbent tier.** What `TIERED-POOL` measured is that **the filter helps on the modern
period** — arm B beat arm A by **+1.06pp of return and +5.98pp of drawdown on 2009-2026** — while
being **bundled with the size bet that sank both arms** (weight under $2B: incumbent **0.0%**, arm
A **37.8%**, arm B **24.1%**; SMB **+0.219 → +0.602 / +0.458**, and *"not one arm's residual is
separable from zero"*). **This arm is the filter without the size bet.**

**Construction — `TIERED-POOL`'s own three screens, unchanged, reused verbatim rather than
re-chosen.** A tier name must satisfy all three (Asness-Frazzini-Israel-Moskowitz-Pedersen 2018):

1. **positive TTM net income** — `_ttm(rows, as_of, ("netinc",)) > 0`
2. **positive TTM free cash flow** — `_ttm(rows, as_of, ("fcf",)) > 0`
3. **leverage not in the worst third of its date's cross-section** — `debt / equity` from
   `fundamentals_pit` on the same as-of row

**`_ttm` IS CALLED, NEVER RE-IMPLEMENTED (`B7`), and that matters for more than tidiness:** it
collapses restatements (`D10-a` — a restatement APPENDS an ARQ row, and 3.15% of
`(ticker, reportperiod)` groups carry more than one `datekey`), requires four distinct quarters,
and refuses a window spanning more than `TTM_MAX_SPAN_DAYS`. **A hand-rolled sum would silently
understate a flow and read as a junk company — the exact direction that would flatter this arm.**

**IT IS A CONSTRUCTION CHANGE, SO IT IS JUDGED ON THE INDEX BOOK, NOT ON AN IC.** Don's rule, both
periods: it must beat the incumbent on **net Roth return** *and* not be worse than the incumbent's
drawdown by more than the **3pp** allowance, on **2009-2026** *and* on the **1999-2008 five-theme
proxy** — each against **that period's own** incumbent. Charter §5 Stage 3's constraint travels
with the proxy leg: it may test an increment on a five-theme base and may **not** validate the
shipped seven-theme construction.

**FREE PRE-OUTCOME KILL (`K1`) — INERTNESS, AND IT IS THE LIKELIEST OF THE SIX TO FIRE.** The
tier is **already large-cap and may already be clean**: `TIERED-POOL` measured **0.0% of incumbent
weight below $300M**, and the whole premise of "size matters if you control your junk" is that
junk concentrates at the **small** end. So the kill measures **the share of tier names failing at
least one screen, per date**, and the arm is **`INERT` and carries no verdict** if the median is
**< 2%**. A filter that removes nothing cannot move a book, and reporting a near-zero change as a
null would be a statement about the book rather than about junk.

**AND A SECOND BOUND IN THE SAME KILL:** the filtered tier must still clear
`CONTRACT_MIN_POSITIONS` = **50** names on **every** date, and the per-date tier count ships, so
the nominal-$10bn drift across 2009-2019 is visible rather than assumed.

---

## 2. B2 — VOLATILITY-MANAGED EXPOSURE ON THE INDEX BOOK *(Moreira-Muir 2017)*

**Construction.** Scale next period's exposure by the inverse of the **previous** period's
realised variance, `w_t = min(1, c / σ²_{t-1}) · w_base`, with `σ²` from **daily** returns of the
Index book inside the prior rebalance window and `c` set so that **average exposure over the build
quadrant is 1.0** — a normalisation, declared before any look, so the arm is not a disguised bet
on holding less.

**THE `min(1, ·)` CAP IS A DECLARED DEVIATION FROM THE PAPER AND THE REASON IS THE PRODUCT.** The
paper levers **up** when volatility is low. **This is a Roth with no margin**, so exposure above
100% is unavailable, and an uncapped overlay would measure a strategy the account cannot run.
Capped, it is *"de-risk in high volatility, never lever up"* — **weaker than the paper's and
honest about it.**

**FREE PRE-OUTCOME KILL (`K1`) — THE LEVERAGE CENSUS, AND IT DECIDES WHETHER THE ARM IS EVEN THE
PAPER'S STRATEGY.** Measure the share of build-quadrant dates on which the **uncapped** scaling
`c / σ²_{t-1}` exceeds **1.0**. If that share is **> 0.50**, the paper's effect is majority-carried
by leverage the account cannot take, and the arm is recorded **`NOT THE PAPER'S STRATEGY`** — run
only as the capped de-risking overlay it actually is, with that label on every figure. No outcome
is touched: this is a census of a scaling factor.

**JUDGED ON DON'S RULE, AND `R1-VAR` IS WHY A SHARPE GAIN IS NOT A PASS.** Don's standing ruling:
**a Sharpe or volatility gain bought with alpha is not worth having unless the Sharpe itself is
bad** — and the book runs **Sharpe 0.5866** at an IR of about **0.88/yr**, so the antecedent does
not fire. **An improvement in Sharpe or realised volatility alone is therefore NOT a pass**, and
the register says so before the numbers exist. It passes only on net Roth return and drawdown,
both periods.

**AND THE LITERATURE'S OWN COUNTER-EVIDENCE IS PRE-COMMITTED AS A PRIOR, NOT DISCOVERED AFTER.**
Cederburg, O'Doherty, Wang and Yan (2020) find volatility management **fails out of sample for
most factors** and that its gains **concentrate in the market factor**. The Index book is not the
market factor, so the prior here is **unfavourable**, and a null is the expected outcome rather
than a disappointment.

---

## 3. B3 — BLITZ-HUIJ-MARTENS RESIDUAL MOMENTUM *(batch 1's A2b, which died on a SEQUENCING blocker)*

**WHY IT RETURNS AND A3/A7/A11 DO NOT.** A2b was **NOT RUN** because its costume bar *"cannot be
evaluated before the SIGNAL exists"* — an **ordering** problem, not an outcome. **The stated fix:
the signal column is built INSIDE THE KILL PASS**, where no forward return is touched, and the
0.60 costume bar is then evaluated on it before any scoring. Building a signal is a census of the
panel's own inputs; under `MB1-SEL` a pre-outcome control can only BLOCK.

**Construction.** 36-month formation window; residual of each name's monthly return on the
**panel's OWN value-weighted market return**, built from the panel's prices; signal is the
*t*-scaled cumulative residual, most recent month skipped.

**DELIBERATELY A ONE-FACTOR RESIDUAL, declared as a deviation from the paper's three**, and the
reason is licensing rather than convenience: Ken French's library is **"free but permission-gated
and factor-level — never a magnitude claim"** (`RUN_RULES` 0.2), so a signal whose construction
depends on French factors could validate a build and **could never ship in a product figure**.
French is used **nowhere** in this arm.

**FREE PRE-OUTCOME KILL (`K1`).** Mean per-date |ρ| against the shipped `momentum` theme **< 0.60**
— and the register pre-commits that **if it lands above 0.50 a pass is read residualised on
`momentum` alone**, which is the reading that killed A11 at 0.7596. Fixing that reading in advance
is what stops a pass being chosen after seeing which one clears.

---

## 4. B4 — ANALYST NEGLECT *(batch 1's A9)* — **CONDITIONAL, and the condition is not mine to meet**

**Construction.** Low analyst coverage as a standalone standardised column: `numest` from IBES
`statsum`, joined on a **dated** `ibes_id` link (`sdates`), scaled by firm size so it is coverage
*relative to what a name of that size usually attracts* rather than a size proxy.

**BLOCKED ON THE DATED IBES LINK, which batch 1 named as "the one concrete thing this batch hands
forward".** Under `MB15` the link is **shared infrastructure and must be validated before any
hypothesis reads it** — the instrument before the hypothesis. **If r1's dated link does not exist
and pass its own validation when the register is written, B4 is NOT RUN and `k` stays 6.** This
draft does not assume it.

**FREE PRE-OUTCOME KILL (`K1`) — THE COSTUME BAR THAT WAS NEVER RUN.** Mean per-date |ρ| against
the **`size`** theme, bar **0.60**. **A neglect proxy is a size proxy until measured otherwise**,
and the record is unambiguous about the direction: `E-1`'s graveyard aggregate died at **0.6114**
against `size`, and `R6`'s conviction signals read **−0.815 to −0.854**. This is the kill most
likely to fire of the three IC arms.

---

## 5. B5 — NET PAYOUT YIELD *(batch 1's A5)* — **the loader blocker, with its cost named**

**Construction.** `(dividends + net repurchases) / market cap` (Boudoukh-Michaely-Richardson-
Roberts 2007), on the argument that repurchases substituted for dividends so dividend yield alone
measures a shrinking share of what is returned.

**ITS BLOCKER IS REAL, BOUNDED AND ON OWNED DATA.** `WRDSProvider._KEEP["fundamentals"]` carries
neither `ncfdiv` nor `ncfcommon`, so the arm needs **new source columns and a panel rebuild** —
the precise reason `S17`/`S19` excluded `S10`'s accounting half. The data is owned; the cost is a
rebuild of the corrected full-universe panel. **It should be batched with any other arm needing
new columns rather than paying that cost alone**, and if no rebuild happens before the register,
B5 is **NOT RUN** and `k` stays 6.

**FREE PRE-OUTCOME KILL (`K1`) — NON-IDENTITY AGAINST THE SHIPPED SIGNAL, BY MEASUREMENT.**
`capital_discipline` is `neg_issuance`, derived in `_yoy()` from `sharesbas` year-over-year.
**`S16` measured that splitting net issuance into buyback and dilution legs is a RANK IDENTITY —
within-date rank correlation `1.000000000000` on all 69 dates — because `max(0, −net)` and
`−max(0, net)` are both non-increasing in `net`.** Net payout yield is **not** that identity (it
adds dividends and rescales by market cap), **but the register must PROVE non-identity rather than
assume it from the construction**: within-date rank correlation against `z_neg_issuance` must be
**< 0.99**, or the arm is the shipped signal rescaled and carries no verdict.

---

## 6. B6 — CAMPBELL-HILSCHER-SZILAGYI DISTRESS PROBABILITY — **a second junk DEFINITION, not a second junk arm**

**Scope, stated so this does not become two answers to one question.** B1 is the **forward
pointer** and uses `TIERED-POOL`'s own three screens. B6 is a **different definition** of the same
idea — a fitted distress probability rather than three accounting cuts — and is ranked **below**
B1 deliberately. **If only one junk arm is run, it is B1.** Batch 1's A4 was withdrawn to avoid
duplicating r1's tiered pool; that pool has now run, so the duplication is resolved by B1 being
the pointer and B6 being labelled an alternative.

**Construction.** The eight CHS (2008) inputs from SF1 + prices — `NIMTA`, `TLMTA`, `EXRETAVG`,
`SIGMA`, `RSIZE`, `CASHMTA`, `MB`, `PRICE` — with the paper's **published** coefficients, **not
re-fitted**. Fitting the filter on this panel and scoring it on this panel is the collapse the
record already paid for: **+8.43%/yr in-search → −0.04%/yr on the locked hold-out**.

**GATED ON A CRASH-RATE RATIO IN BOTH HALVES, NOT ON ALPHA AND NOT ON DRAWDOWN, and that is forced
by measurement rather than chosen.** `S10` measured this book's maximum drawdown as spanning
**exactly ONE 63-day period on every arm, at the same trough index 44 of 69 — COVID 2020Q1** —
which **no name-level screen can move**; `S10-ACCT` then failed precisely that leg while
*improving* alpha by **+0.1970pp**; and **X7 calibrates no drawdown floor anywhere**, so a
drawdown bar would be uncalibrated (§6). `MA28-CARD` is the design that worked on this shape.

**FREE PRE-OUTCOME KILL (`K1`).** Input coverage on the **tier** (the governing population) at the
**0.70** non-null rule, measured on the arm's own rows — `O-1` applied an alert-book figure to the
panel and was **~17× wrong**. `PRICE` and `RSIZE` are price-derived and safe; `TLMTA` and `CASHMTA`
need balance-sheet items whose coverage on this universe is **unmeasured**, and `POOL-SIZE`
measured a worst-theme missing rate of **0.1956 even over $10B**.

---

## 7. WHAT IS DELIBERATELY NOT IN BATCH 2, AND WHY — *named so none of it reads as an oversight*

**Died on their OUTCOME, so they do not come back** (the brief's own instruction, and the right
one — re-running an arm that failed its own pre-committed reading until it passes is the thing the
whole protocol exists to prevent):

* **A11** 52-week-high proximity — cleared BH at *p* 0.00136, then failed its pre-committed
  momentum-only reading (44 dates at +3.3356, early **+1.596** against late **+3.912**).
* **A3** information discreteness — *p* 0.12508.
* **A7** net issuance — *p* 0.65298.

**A1 — intangible-adjusted value — is NOT in batch 2, and this is the judgement most worth
stating.** Its coverage kill fired at **0.6087** against 0.70, at W-28's **externally anchored
10-fiscal-year** burn-in. Batch 1 also measured **0.8452 / 0.7620 / 0.6638 at 3 / 5 / 8 years**,
and recorded the counterfactual that **at 3 or 5 years the kill would NOT have fired.** **So
re-running A1 at a shorter burn-in is choosing the parameter on the outcome** — the register's own
amendment refused to do that prospectively and it must not be done retrospectively either. **A1
returns only under a burn-in anchored by something external that predates the look, and no such
anchor exists beyond the 10-year one that already fired.**

**A6 — small/mid core — is excluded for TWO reasons, either sufficient.** Its ADV name coverage
read **0.3905** (944 of 3,545) because the ADV inputs were built on the **restricted** universe, so
the band quietly became *"small AND present in the old ADV input"* — and there is **no stated fix
on owned data** (`B13_ADV_PANEL`'s cell overlap with a re-gridded panel is **zero**). Separately,
under charter **Stage 1b the tier governs**, and a sub-$10B band **cannot advance by construction**
— so even a clean coverage fix would leave it `REAL BUT NOT INVESTABLE HERE`.

**A10 — industry momentum — is excluded on coverage with no owned-data fix:** dated-GICS coverage
**0.3713** on this universe. `S25`'s map reaches 94.8% of the **old** 2,441-name panel; extending
it to 9,645 names is **a data pull, not an analysis**.

**`IDEAS_LEDGER.md` CONTRIBUTES NOTHING, AND THAT IS A FINDING RATHER THAN AN OMISSION.** Its
season portfolio **E-1 through E-6 is fully spent** — all six are `DONE` in the ledger: `E-1`
**WITHDRAWN** on its `K2` (the arm never ran), `E-2` **NULL** on both co-primary bases, `E-3`
**NULL** on both, `E-4` **UNDERPOWERED** on a pre-committed three-state rule, `E-5`
**UNRESOLVED** on a pre-committed conjunction, `E-6` **NULL** on both bases. Its `PARKED` list is
options-lane (`MB15-SLIM`, conformal bands), licence-blocked (`JKP-S22` — research-only, product
never), already landed (`SC-1b`), or needs data this project does not own (`S-SEED-6b` peer
momentum, which runs on customer-list and shared-analyst link data). **The ledger is August-era
and superseded by the staged protocol; it holds no remaining equity candidate buildable on owned
data.**

**Volatility-managed exposure was "noted, not drafted" in batch 1 and IS drafted here** (B2),
because the brief asks for it — with `R1-VAR`'s ruling cleared in writing first, as that batch
required.

---

## 8. WHAT THIS DRAFT DOES NOT DO

* **No register committed, no arm run, no trial booked, nothing measured.** `k` = 6 is a plan.
* **No Stage-2 look.** The check quadrant stays closed; looking at it to choose among these six
  would spend it with no replacement.
* **No Stage-3 look.** B1 and B2's 1999-2008 legs are part of **their own** construction-level
  rule under Don's ruling, and they inherit charter §5's constraint: a five-theme proxy may test
  an increment and may **not** validate the shipped seven-theme construction, with `POOL-SIZE`'s
  prior read disclosed.
* **The 1972-1998 WRDS era stays closed** — `OOS1`'s Gate B reads **0.837303** against its
  pre-committed **0.90**.
* **Nothing is adopted.** Adoption is Don's, is a vintage event, and quotes the expected return at
  **half** the backtested size (McLean-Pontiff).
* **B4 and B5 may be NOT RUN on their own blockers**, and `k` stays 6 either way.
* **B6 is withdrawn if only one junk arm is to be run** — B1 is the pointer.
