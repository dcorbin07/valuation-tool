# PREREG — REBAL-CADENCE: how often should the Index rebalance?

**Committed BEFORE any arm is scored against any bar.** Markdown only, zero `.py`, and a strict
git ancestor of every commit that computes an outcome. The three equity trials are booked in
their own commit before the scoring runner exists.

---

## 0. State of the counter, re-read rather than quoted

`research_log.detail()` on the merge base of this register:

> `by_domain` = **equity 248, options 310, unified 0, infra 20**

Equity `N` = **248**, so `sqrt(2 ln 248)` = **3.3206712412296953**. This register books **3
equity trials** → `N` = **251**, `sqrt(2 ln 251)` = **3.3242903**. Both derived, neither typed
from a handoff (`MA19`, `MA37`).

**NO PERMUTATION FLOOR CAN MOVE.** `MB31`'s mechanism: `N` reaches a calibrated floor ONLY
through the CPCV adopt gate, so a floor moves only when a banked draw FLIPS. The next flip is
seed **1017 at `N` = 688** — 437 trials out — so every X7 floor is provably unmoved at 248 and
at 251. (`CLAUDE.md` still names seed 1003 at `N` = 247; that trigger fired at `W-1` and the
map was repaired. **Derive it; do not quote a countdown.**) Nothing here reads a permutation
floor in any case — see §4.

---

## 1. The question, and why it is not already answered

`S22` measured top-decile alpha **still accruing at two years** — annualised **+6.6%** at three
months against **+5.1%** at two years — while a name typically stays in the decile for **ONE
quarterly rebalance**. The book pays **~261%/yr** turnover at a measured **33.4 bps** one-way.
So the shipped cadence harvests a quarter of an edge that persists for eight, and pays to do it.

`S22` also says, in terms: *"it is NOT a finding that the book should rebalance less often"* —
because `cum_alpha(H)` is the buy-and-hold return of a cohort selected on ONE date, while a
quarterly book **re-selects and compounds fresh selections**. Those are different claims and
only the first is measured. **This register is the test `S22` named and declined to run.**

Two prior results bound the design before it starts:

* **`S23`: never-selling costs 10.89pp/yr, and the mechanism is DILUTION rather than friction.**
  A book that keeps buying accumulates cohorts of every age and converges on a 417-name slice of
  the universe. So *"hold longer"* must mean a **FIXED-SIZE book re-formed on a slower clock**,
  never a book that stops selling. Every arm here re-forms a book of the same size.
* **`S23` also found no exit rule beating the incumbent**, so the cadence question is about the
  CLOCK and not about the exit condition, which is already tested and settled.

---

## 2. The arms — these four and no others. NO GRID.

On the corrected **69-date quarterly panel** (`panel_corrected_69d.pkl`, 2,531 names), the
**contract book**: top decile of the large-cap tier, 30% no-trade band, flat 1/7 weights, scored
through the shipped `turnover_and_costs` with `top_frac=0.1, exit_frac=0.3, horizon=63` — the
exact call that produces `BACKTEST_RESULTS.json` `book_configs.taxable`.

| arm | construction | trials |
|---|---|---|
| **1. quarterly** | cadence 1 — the incumbent, and the control everything is paired against | **0** |
| **2. semi-annual** | cadence 2, offset 0 | **1** |
| **3. annual** | cadence 4, offset 0 | **1** |
| **4. staggered** | four cadence-4 sub-books at offsets 0,1,2,3 — one re-formed each quarter, 25% of capital each | **1** |

**Arm 1 charges nothing because it is a REPRODUCTION, not a search** — it must reproduce the
published contract book to tolerance or no arm runs at all (§5, `K1`). That is the `C1` class and
the `X7`/session-10 precedent for a calibration charging zero.

**THE MACHINERY IS EXTENDED, NOT RE-IMPLEMENTED (`B7`).** `turnover_and_costs` gains
`cadence`, `offset` and `return_series`, all **opt-in and inert by default**, so the band, the
market-cap cost table, the weight drift and the formation rule stay in one place. Re-implementing
any of them would be the defect `B7` exists to prevent. The staggered combination is the only
study-side logic and lives in `valuation/studies/rebal_cadence.py` (`MA23`: a study, so nothing
under `web/`, `saas/` or `screener/` may import it).

**WHY ARM 4 IS NOT MERELY A FOURTH CADENCE.** Jegadeesh-Titman overlapping portfolios keep an
annual **holding** period while using **every** quarter's signal, and they remove the one thing a
single-offset annual book cannot escape: **`X2` measured the rebalance-date grid ALONE moving the
long-short *t* from 2.70 to 3.52 on this panel.** So *"annual, formed in January"* is partly a
measurement about January. **Arms 2 and 3 carry timing-luck exposure BY CONSTRUCTION; arm 4 does
not.** The offset sweep for arms 2 and 3 therefore ships as a **labelled diagnostic carrying no
verdict and no trial** — it quantifies the luck rather than choosing a winner from it, and
picking the best offset after seeing it is the design-on-outcome this record forbids.

**TWO CONSTRUCTION DECISIONS, DECLARED BECAUSE EITHER COULD BE GOT SILENTLY WRONG.**

1. **The book return is WEIGHT-WEIGHTED on a held period.** The shipped line is
   `np.mean(rets)`, correct only because a rebalance resets the book to equal weight. After a
   quarter of drift the weights are not equal, so an unweighted mean would report the return of
   a book that *had been rebalanced* — handing the long-hold arms the incumbent's rebalancing for
   free, in the direction that **flatters the hypothesis**. `sum(w_i r_i)` equals `np.mean` to
   floating point when weights are equal — **not to the bit in general, because `np.mean` sums
   pairwise and `np.dot` does not**; a first draft of this clause claimed bit-equality and the
   test written to pin it FAILED, correctly. The bit-identity that matters is the one on THIS
   panel, and it is MEASURED by `K1`/`K2` reading 0.000e+00 rather than inferred from the algebra.
2. **A held name that leaves the panel is DROPPED, the remainder renormalised, and the dropped
   WEIGHT counted rather than priced.** `fwd_ret` already carries a terminal value for a delisted
   name (`E-5`), so a missing ROW is an absent observation rather than a loss, and imputing zero
   would invent a return. **A DEFECT OF MY OWN HERE, CAUGHT BY ITS OWN TEST BEFORE THIS REGISTER
   WAS COMMITTED, AND IT RAN AGAINST THE HYPOTHESIS:** the first cut derived a held period's trade
   from `|target − drifted|`, which read that renormalisation as BUYING more of each survivor and
   charged **0.0661 of two-way turnover per cadence-4 held period** — so every long-hold arm was
   paying a cost to hold, which is exactly the direction that makes slowing down look worse than
   it is. A hold period now charges **nothing**, and the dropped weight is reported so `K4` can
   read the hole instead of the cost model swallowing it.

**EVERY ARM IS SCORED ON ONE DATE SET** — the intersection across all four — so no paired
difference is partly a difference of windows. The staggered arm binds it: four sub-books at
offsets 0..3 are all live only from the 4th panel date. **Measured in pass 0: 66 common periods,
2009-10-15 to 2026-01-28.**

---

## 3. Primary metric, and the gate

**PRIMARY: net-of-measured-cost annualised top-decile alpha versus the equal-weighted universe**
— `turnover_and_costs`'s `net_alpha`, which **COMPOUNDS** (its own docstring says so, and warns it
will not tie to `construction.*`, which annualises arithmetically; the two differ by ~2pp and
mixing them is how a cost figure gets compared with a construction figure).

Scored as a **PAIRED per-period difference against arm 1** on the common dates, with a
**Newey-West HAC(1)** standard error. Lag 1 is this panel's own convention: the 63-day windows do
not overlap, and `R9` measured lag-1 autocorrelation +0.189 on the long-short spread and made the
HAC figure the one quoted. **The equal-weight benchmark cancels out of a paired difference of net
alphas** — both arms face the same per-date benchmark — so `net_k − net_1` IS the paired alpha
difference, and subtracting the benchmark again would be double-counting.

**THE GATE IS `SECTOR-NEUTRAL-B6`'s, REUSED VERBATIM** — as `W-1` and `PKG-MB20` did, so the bar
has precedent and is not chosen on this data:

> **Δ net alpha > +100 bps AND Δ HAC *t* > +0.25, in BOTH halves.**

Halves = the 66 common periods split in two with the **boundary period embargoed**, because a
cadence-4 formation spans the boundary. The realised counts are reported, not assumed. Both
halves must clear; a sign flip between halves fails in either direction. **An arm clearing both
legs in both halves is recorded `ELIGIBLE`, never adopted** (§8).

**Ambiguous against a pre-committed threshold is a NULL** (`RUN_RULES` A6).

---

## 4. THE MDE, MEASURED BEFORE THE RUN — and the margin sits BELOW it

`RUN_RULES` A11 requires this before the run, and `MB8` forbids borrowing an `se` across
perturbation sizes, so the paired HAC se was **measured on these arms** in a pre-outcome control
pass (`scripts/rebal_cadence_control.py`). `R1-VAR` licenses that ordering explicitly: such an
arm *"needs its OWN measured paired SE — a CONTROL, which under `MB1-SEL` can only BLOCK and
therefore costs ZERO TRIALS and may be taken BEFORE any register is written."*

**That pass emits DISPERSION ONLY — `n`, the paired HAC se, and the thresholds that follow. No
mean, no alpha level, no *t*, no verdict, for any arm** — so running it could not reveal which
way any arm came out, and this register is still blind to the outcome. Enforced by an AST test
over the control script plus a key-level check on its artifact, not promised in prose.

Measured, on 66 paired periods, annualised (× 4):

| arm | paired HAC se | MDE 50% power | **MDE 80% power** | MDE80 at the HLZ hurdle 3.3207 |
|---|---|---|---|---|
| semi-annual | 0.8665 pp | 1.7329 pp | **2.4607 pp** | 3.6050 pp |
| annual | 1.0586 pp | 2.1171 pp | **3.0063 pp** | 4.4043 pp |
| staggered | 0.6991 pp | 1.3982 pp | **1.9854 pp** | 2.9087 pp |

**THE CONSEQUENCE, STATED NOW RATHER THAN DISCOVERED LATER: the +100 bps margin is 2.0x to 3.0x
BELOW the 80%-power MDE at the conventional crit, and 2.9x to 4.4x below it at the honest
hurdle.** Two things follow and both bind the write-up:

* **A PASS IS NOT A DETECTION.** The alpha leg is a bar on the POINT ESTIMATE, so an arm can
  clear +100 bps while its difference is not separable from zero. Any `ELIGIBLE` verdict must be
  reported with its own *t* and this MDE beside it, and **may not be described as a demonstrated
  improvement.**
* **A NULL IS BOUNDED, NOT ABSENT.** A null here means *"no cadence effect as large as roughly
  2 to 3 pp/yr"*, never *"cadence does not matter"*. `S19` and `V6` both published nulls their
  designs could not have distinguished from a true effect; this one states the bound up front.

**EVERY CRITICAL VALUE IS LABELLED UNCALIBRATED.** `V2G` established and `R1-VAR` re-confirmed
that **no calibrated floor exists for a paired within-panel difference**; `X7` calibrates
LEVELS. So the 2.0 and the 3.3207 are conventions, and no X7 floor is quoted anywhere in this
register.

---

## 5. Kills, declared before any arm is armed. `--arms` refuses without a passing control artifact.

| | kill | bar | consequence |
|---|---|---|---|
| **K1** | the incumbent reproduces the published contract book — `net_alpha`, `net_sharpe`, `net_max_drawdown`, `annual_turnover` from `book_configs.taxable` | max abs dev <= 1e-12, **and all four fields compared** | no arm is scored; the item stops |
| **K2** | `cadence=1, offset=0` is bit-identical to the shipped default | exact, 0.0 | the extension is not inert; stop |
| **K3** | the cadence is NOT inert — annual turnover must fall materially | annual arm's `annual_turnover` <= 0.70 x the quarterly arm's | a verdict on an inert intervention is meaningless; report INERT and score nothing |
| **K4** | holding is not measuring attrition — held names that leave the panel | dropped held name-periods < 5% of held name-periods | the long-hold arms are an attrition study; report and withdraw |
| **K5** | the staggered arm has exactly 4 live sub-books on every scored period | 4 of 4, every period | it is not a four-book average; withdraw arm 4 |

**K1 and K2 are gating and ran in their OWN pass, read before any arm was scored** — `O10`'s
process defect, not repeated. Both PASS: K1 worst deviation **1.110e-16** on
`net_max_drawdown` (last-digit float; the other three are **0.000e+00**), K2 exact.

---

## 6. Secondary, EXPLICITLY NO VERDICT

Reported because a reader would otherwise ask, and carrying no bar and no trial:

* **vs SPY**, through the shipped `benchmarks` convention.
* **Turnover** per arm, and the realised turnover-weighted one-way bps actually charged.
* **After-tax**, through the shipped `after_tax_backtest` — and it is the one secondary with a
  mechanism worth stating in advance: **an annual hold crosses the long-term capital-gains
  line** (`LONG_TERM_DAYS = 366`, and the lot clock runs on the real calendar), so the after-tax
  leg should favour the slow arms even where the pre-tax leg does not. That is a **TAXABLE-account
  statement only**; a Roth/IRA pays no such drag.
* **Max drawdown**, net.

**DON'S STANDING RULING (`R1-VAR`) BINDS ALL OF THESE: a volatility or Sharpe gain bought with
alpha does not count.** The book runs Sharpe 0.5866 at an IR of ~0.88/yr vs SPY, so the
antecedent of that ruling's exception does not fire. **No secondary may convert a failing primary
into an eligible arm**, and `X7` calibrates no floor for Sharpe, drawdown, turnover or
after-tax, so each is a measurement carrying no verdict.

---

## 7. OUT OF SCOPE, stated and not tested: MONTHLY

**A monthly cadence is NOT an arm here and no monthly figure will be reported.** It needs
`MA33`'s monthly panel rebuild, and three costs that are not in the audit's estimate:

1. **The rebuild itself.** Feasible on owned data — `bulk.prepare_daily` already down-samples
   DAILY to one row per ticker-month, so monthly is the *native* granularity of the
   point-in-time market-cap path — at roughly **3x** the 69-date build's ~20 minutes, **on every
   build thereafter**.
2. **ITS OWN PLACEBO CALIBRATION.** Every X7 calibrated bar (2.2837, 2.7072, 1.8629pp, 19.667%)
   is calibrated for THIS panel at 69 dates, so on a monthly panel each becomes an
   **EXTRAPOLATION** and a monthly result could carry no verdict until a fresh placebo sweep
   exists. That sweep is the dominant cost and the audit's estimate omits it.
3. **THE `prepare_daily` STALENESS DEFECT, INHERITED AND WORSE.** `S8`/`S9` measured the
   point-in-time market cap as **up to 31 days stale** against a same-day price. On a quarterly
   panel that is a precision defect; **on a monthly panel it is a third of the rebalance
   interval**, so `size` — the theme `X3` measured as carrying the composite's entire statistical
   significance — would be scored against a stale denominator a third of the time.

A **recommendation on whether it is worth building** is required output and is given in the
write-up **after** arms (1)-(4) are read, because the answer depends on them: the direction
established by a quarterly-to-annual sweep is the evidence about whether moving the clock the
*other* way is worth three costs. Stating the recommendation here would be deciding it without
the evidence this register exists to produce.

---

## 8. ADOPTS NOTHING, and a cadence change is a VINTAGE EVENT

The cadence is part of the construction, so changing it **ships in the live scoring path** and
is a vintage event under `PAPER_TRACK_CONTRACT.md` §5a — it closes the current vintage and opens
the next, **resetting the whole accrued five-year clock for zero statistical gain** (`RUN_RULES`
rule 6, and `S14`'s own routing). The current vintage is **DERIVED from `track_meter.VINTAGES`
at write-up time and never quoted from a handoff** (`PT-GAPDUE`; three resets in four days is
why).

**So an arm clearing the gate is recorded `ELIGIBLE — ROUTED TO DON` and is not adopted here.**
`CONFIG` is untouched, `settings.BOOK_CONFIGS` is untouched, no live path changes, and the
banked panel is not overwritten — pinned by test.

---

## 9. Void conditions

1. **No grid.** Four arms, the cadences named in §2 and no others. Reporting a fifth cadence, or
   any cadence chosen after seeing a result, voids the item.
2. **No offset selection.** The offset diagnostic for arms 2 and 3 carries no verdict. Quoting
   the best offset as an arm's result voids the item.
3. **No bar relaxed after watching it fail** (`W-28`'s closing rule, and `§6`'s own).
4. **No secondary promoted to primary.** `R1-VAR` and §6.
5. **No X7 floor quoted** on any paired difference (`V2G`, `R1-VAR`).
6. **The MDE travels with the verdict.** A null reported without §4's bound, or a pass reported
   without its *t* and that bound, voids the write-up.
7. **No monthly figure**, per §7.

---

## 10. Expectations, registered before the arms are scored

Scored honestly afterwards, wrong or right.

| | prediction | odds |
|---|---|---|
| 1 | **All three arms NULL on the primary.** The record's base rate is overwhelming, and the margin sits below the MDE | 70/30 |
| 2 | **The annual arm is the WORST of the three on net alpha.** `S22`'s cohort result does not transfer to a re-selecting book, and a year-old signal on a panel whose names leave the decile in one quarter is mostly stale | 60/40 |
| 3 | **The staggered arm is the BEST of the three.** It keeps every quarter's signal while holding a year, which is the only arm that does not throw signal away | 65/35 |
| 4 | **Turnover falls roughly in proportion to the cadence** — annual near a quarter of quarterly | 75/25 |
| 5 | **The after-tax leg favours the slow arms even if the pre-tax leg does not**, because an annual hold crosses the long-term line | 80/20 |
| 6 | **`K3`, `K4` and `K5` all pass** | 85/15 |
| 7 | **At least one arm's halves disagree in sign** — this record's single most repeated pattern | 70/30 |

---

## 11. What this register does NOT claim, whatever it returns

* It does not re-open `S22`, whose four nulls and whose term-structure result stand. A cadence
  null here is **not** evidence against persistence; it is evidence that a re-selecting book
  cannot harvest it by slowing down.
* It does not re-open `S23`, `S14` or the exit-rule family.
* It says nothing about a **monthly** cadence (§7), nothing about the `roth` 42-day config, and
  nothing about the `enter_frac`/band width `S14-WIDTH` already closed.
* It licenses no trade and changes no product copy.
