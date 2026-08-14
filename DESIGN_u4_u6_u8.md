# DESIGN MEMOS — U4, U6, U8

**These are design records, not measurements.** No hypothesis is registered, no threshold is
pre-committed, no verdict is issued and **no trial is charged** (session 8's precedent for
declining a test that cannot resolve, and S25's for closing a row on a fact about what data
exists). Where a memo states a number, that number is a measured fact about the data or the code
and is labelled as such.

Each row closes **`DESIGN-RECORDED`**: the design question has been answered — *what would this
have to look like to be worth building, and is it buildable now?* — without manufacturing a
backtest where the honest deliverable is a memo.

**The constraints below are shared by all three memos.** They are measured verdicts from this
project's own record, not opinions, and every design here is built to respect them:

| # | Constraint | Where it was measured |
|---|---|---|
| K1 | **The options entry signal is dead.** The alert book loses to random-day entry by **−5.0640pp/trade** (sign test z −4.9612, p 7e-07). | `R2`, split-clean at `U1-SPLIT` |
| K2 | **The equity composite carries no information about which alert to take or refuse.** Veto lift −0.57pp; entry arm −1.1892pp against its own null. | `U7`, `U1` |
| K3 | **The options surface carries no information about stock returns.** All four arms rejected; incumbents explain only 5.5–8.8% of the features' variance. | `U2` |
| K4 | **Positive per-trade expectancy loses money at realistic sizing.** +3.27%/trade ends at **$37,059 from $50,000** at a concurrency cap of 10; max drawdown 0.6710. | `O11` |
| K5 | **Per-bucket expectancy on this book is essentially unmeasurable.** Half-to-half sign agreement is a coin flip at every bucket size; ~6,148 trades needed, the whole book is 3,870. | `O26` |
| K6 | **The sleeve is not insurance — it is leverage.** Correlation with the equity book **+0.4371**; in the equity book's worst quarters the sleeve returns **−84.39%**. | `U3`, this session |
| K7 | **The equity book is investable only in part.** `B13` is `PARTIAL — BLOCKED ON DATA`: no liquidity measure exists on the panel path, so `avg_dollar_volume` cannot be computed at all. | `S7`/`S18` |

---

## U4 · One decision object

**Audit:** `VALQUO_EDGE_AUDIT.md:1290`. **Ledger row:** `src=human`, *"Deliberately gated on
U1/U2 — do not ship over two disconnected engines."* **That note is accurate, and the gate it
names has now resolved.**

### What the gate returned

The row was gated on U1 and U2. Both have run, and **both rejected** — as did U7, the cheaper
probe of the same hypothesis. So the question the gate was asking is answered, and the answer is
the unfavourable one: **there is no measured signal relationship between the equity composite and
the options book in either direction.** K1, K2 and K3 are the three independent legs of that.

This matters for the design, because the audit's framing assumes the unification would be a
*signal* unification — *"the fundamental view, its confidence, the recommended expression"*. A
recommended expression implies the expression is derived from the view. **It is not, and three
registers now say so.**

### What can honestly be built

Not one object with one recommendation. **One object with two independently-sourced expressions
and an explicit statement that they are independent.** Concretely, per name:

1. **The fundamental view** — composite, theme breakdown, decile, and the caveat the record
   already requires (`V2G`: the live product scores a **four-theme** book, 42.9% of the weight
   mass being inert live, and the live four-theme book **fails** the calibrated long-short floor
   at HAC *t* 1.8811 vs 2.2837 while clearing the top-decile alpha floor).
2. **The options expression, if one exists**, labelled with what is measured about it: it is
   **not** derived from the view (K2), its entry timing has **no** demonstrated edge (K1), and
   its per-trade expectancy is positive while its **survivability at realistic size is not**
   (K4).
3. **No combined score, no combined confidence, and no arrow from one to the other.** Any glyph
   implying the fundamental view endorses the options trade would assert exactly the
   relationship U1, U2 and U7 each failed to find.

### The copy constraint the audit gets right and the product must keep

`:1296`: the options profile is convex with a ~37% hit rate and **must be framed as expectancy,
never as win probability.** A user reading "high confidence" as "likely to win" abandons after
four losses, which on this distribution is an ordinary run. This is already right internally;
the memo records it so a presentation layer cannot quietly lose it.

**One addition this session forces.** K4 means expectancy framing is *necessary but not
sufficient*. A user told "positive expectancy per trade" and given a $50,000 account will
reproduce O11's −25.9% result. **Any surface quoting per-trade expectancy must quote the
survivability result beside it**, or it is technically true and practically misleading.

### Verdict

**`DESIGN-RECORDED`. Buildable now, and materially cheaper than the audit imagined** — because
the expensive part was the unified signal, and the research says there is not one to build.
It is **product work, not research**, and it belongs to the **web/app lane**, not this one. It
should not be reported as U4 being *done*; it is U4 being *specified*.

---

## U6 · Cash-secured puts in, covered calls out

**Audit:** `:2091`. **Ledger row:** `src=human`, *"Session 7 (the unification), after U1."*
Accurate. The audit calls this *"the most immediately tradeable idea in Part V"* and *"absent
from every roadmap"*, at Effort M.

### THE BLOCKER IS MEASURED, AND IT IS COVERAGE — 1.81%

The audit's method (`:2103`) is: *"Replay the equity book's entries and exits over the panel,
substituting the option expression, using the mined chains for the names where they exist."*
That last clause is the whole problem, and it is measurable.

Measured on the corrected 69-date panel against the 187-name mined options universe:

| quantity | measured |
|---|---|
| equity top-decile size | **165.6 names** per rebalance (mean) |
| names **ENTERING** the decile, all 68 transitions | **7,132**, of which **129 have mined chains = 1.81%** |
| names **LEAVING** the decile | **7,095**, of which **128 have mined chains = 1.80%** |
| covered entries per rebalance | **median 2**, max 8, and **ZERO on 18 of 68 dates** |
| restricted to the options window (41 dates) | **82 of 4,490 = 1.83%**, median 2 |

**So the replay the audit specifies would substitute the option expression on a median of two
names out of a 166-name book.** That is not a test of U6; it is a rounding error wearing a
test's name. And on 18 of 68 rebalances it would substitute nothing at all while still
producing a number.

### ~~A SECOND, INDEPENDENT BLOCKER: THE PUT SIDE HAS NEVER BEEN MINED~~ — **RETRACTED 2026-08-13 (V6-OPT). THIS BLOCKER DOES NOT EXIST, AND IT WAS HALF THE STATED REASON FOR CLOSING THIS ROW.**

**What this section said, kept verbatim because the error is the instructive part:**

> `U6`'s entry leg is a **cash-secured put**. The banked options book is `opt_right == "call"` on
> **3,870 of 3,870 rows** — 100% calls, measured. The mined cache was built for a long-call alert
> strategy, so there is no banked put-chain history to replay a CSP against. The derived layer
> carries `iv_put_25d`, which is an implied-vol surface point, **not a tradeable put quote with a
> bid, an ask and an open interest** — and O18 measured that spread cost on this book is
> **ρ = 0.6743 of the quoted half-spread**, so a CSP study without quoted put spreads would price
> the one leg that decides the answer by assumption.

**THE MEASUREMENT IS RIGHT AND THE INFERENCE FROM IT IS WRONG.** `3,870 of 3,870` is a fact about
the **traded book** — the contracts the alert strategy happened to buy. It is not a fact about the
**chain cache**, and the cache was never checked. Measured (`scripts/v6opt_premise.py`, artifact
`data/free_analysis/V6OPT_PREMISE.json`), on 40 randomly sampled tickers and 2,577,501
contract-days:

| | measured |
|---|---|
| puts in `data/options` | **1,288,750** |
| calls | **1,288,751** |
| put share | **exactly 0.5000** |
| tickers with **zero** puts | **0 of 40** |

The cache stores **full chains, both rights**, with `bid`, `ask`, `volume` and `open_interest`;
`data/options_derived` carries the same contracts with `iv`, `delta`, `mid` and `spread_frac`.
**So quoted put spreads exist, and `V6-OPT` went on to price 2,038 real 25-delta puts from them
and settle them to expiry.** The third requirement below — *"point-in-time quoted spreads on those
puts"* — was already satisfied when this memo was written.

**The FIRST blocker (1.81% chain coverage of the equity book's own entering names) is untouched
and still stands**, so `U6` as the audit specifies it — replaying *the equity book's* entries —
remains not buildable. But it is now blocked on **one** measured reason, not two, and the row is
corrected in the ledger to say so. **The lesson is the transferable part: a composition fact about
a BOOK is not a coverage fact about a CACHE, and this lane has now made that exact substitution
twice** — the other being `O13`'s `opt_right` degeneracy, which is the same observation used
correctly.

### What it would take to be worth building

1. **A put-chain mine over the equity book's own names**, not over the 187 megacaps the alert
   universe was built from. The binding constraint is the *equity* book's composition, and the
   two universes overlap at 1.81%.
2. **Point-in-time quoted spreads on those puts**, because the audit's own honest-risk paragraph
   (`:2101`) says the test *"must measure the give-up as carefully as the pickup"*, and the
   give-up is a spread-and-assignment question.
3. **A pre-registered treatment of the right tail.** `:2101` is explicit that this is a
   *return-shaping* trade, not a return-increasing one. On a momentum-inclusive composite some
   exiting names rip, and `S22` measured that this book's top-decile alpha is **still accruing at
   two years** — so a covered call written on a name leaving the decile is being written on a
   population whose forward return is measurably not zero.
4. **It inherits K5 as a prior.** Per-bucket expectancy on options books this size is a coin
   flip between halves; a CSP study on ~2 names per rebalance would be far below even that.

### Verdict

**`DESIGN-RECORDED — NOT BUILDABLE ON DATA WE OWN.** The reason is measured (1.81% chain
coverage ~~, 100%-call cache~~ — **the second half of that parenthesis was RETRACTED on
2026-08-13, see above; the coverage blocker alone carries the verdict**), not asserted.** Same
class as `S25` (point-in-time sectors) and the
`B13` liquidity blocker: the honest close is *unobtainable without new data*, and inventing a
proxy universe would answer a different question under this one's name. **It remains the most
tradeable idea in the catalogue if the data is ever bought** — the audit is right about that,
and nothing measured here contradicts it.

---

## U8 · One risk budget across both books

**Audit:** `:2123`. **Ledger row:** `src=auto`, *"no mention anywhere in the corpus"* — **wrong,
and corrected as part of this item.** The audit's argument: the equity book sizes by equal weight
within a decile, the options book by a fixed dollar risk budget per trade, *"neither knows the
other exists"*, and *"a volatility event that fires twenty options alerts simultaneously is also
the event in which the equity book is drawing down, and nothing anywhere accounts for that."*

### THE AUDIT'S CENTRAL EMPIRICAL CLAIM IS NOW MEASURED, AND IT IS CORRECT

This is the one part of U8 that did not need a new study, because `U3` and `O11` between them
measured it this session and last:

* **O11** measured that alerts **cluster**: over 483 weeks, median 7 alerts and max 38, with
  **51.5% of all trades in weeks of more than 10 alerts**.
* **U3** measured that those are the same episodes: the sleeve's correlation with the equity
  book is **+0.4371**, and in the equity book's worst quarters the sleeve returns **−84.39%**
  against its own **+27.52%** average quarter. In COVID 2020Q1 the equity top decile fell
  **−28.09%** and the sleeve fell **−76.14%**.

**So the audit is right that the exposures coincide, and it is right that nothing accounts for
it. What it did not anticipate is the direction.** Its own framing (`:2127`) imagines the
options book firing *more* trades into an equity drawdown — a **concentration** problem. The
measured problem is worse than that and is different in kind: the options sleeve does not merely
add exposure during the equity drawdown, **it loses roughly three times as much as the thing it
was supposed to be diversifying.**

### Why the audit's prescribed method cannot be run as written

`:2129` prescribes: *"Allocate between the two arms by their measured contribution to combined
drawdown rather than by a fixed split. Use the Ledoit–Wolf machinery already built for the VRP
arm, applied across arms rather than within one."*

Three problems, in ascending order of severity:

1. **The allocation it would produce is already known, and it is a corner.** U3 swept exactly
   this allocation over X ∈ [90, 99] at two concurrency caps — 20 cells — and **maximum drawdown
   was worse than the equity book alone in every one of them**, monotonically improving toward
   X = 100. An optimiser minimising combined drawdown over this pair puts **zero** in the sleeve.
   A shrinkage estimator is not needed to find a corner solution that a 20-cell sweep already
   found.
2. **Ledoit–Wolf shrinks a covariance matrix toward a structured target, and with two arms there
   is essentially nothing to shrink.** The machinery earns its keep on many correlated assets;
   on a 2×2 it is close to an identity operation. Reaching for it here would be sophistication
   as decoration.
3. **The drawdown estimate it would optimise rests on ONE episode.** `S10` measured that this
   book's worst peak-to-trough spans **exactly one 63-day period at trough index 44 of 69** —
   COVID 2020Q1. U3 measured **5** distinct equity drawdown episodes deeper than 5% on the
   covered subsample, but only one of severity. **Allocating on a contribution-to-drawdown
   estimate fitted to one crash is fitting a portfolio to a single observation**, which is the
   in-sample selection this project has already paid for once (+8.43%/yr in-search →
   −0.04%/yr locked hold-out).

### What can honestly be built, and it is smaller and more useful than an optimiser

A **combined exposure report**, not an allocator:

1. **One capital base, stated.** Today the two books are sized against different, unstated
   notionals. Simply writing down that they draw on the same capital is most of the value, and
   it needs no estimation at all.
2. **A concurrency-aware exposure line**: open options premium at risk, plus equity book value,
   as a fraction of one capital base, reported through time. O11's marks already support this.
3. **A named, pre-committed cap on the options sleeve's share** — chosen as a *policy*, not
   fitted. U3's sweep says the drawdown-minimising choice is zero and the Sharpe-maximising
   choice is a return effect that the audit's own bar disqualifies, so **there is no fitted
   number worth having here** and a policy cap is the honest instrument.
4. **A tripwire, not an optimiser**: flag when the alert rate enters O11's top decile of weeks,
   because that is measurably the moment when both books' exposures rise together.

### Verdict

**`DESIGN-RECORDED`.** The measurement U8 depended on (`O11`, and now `U3`) has been done, and it
**refutes the premise of the prescribed method rather than enabling it**: a
contribution-to-drawdown allocator over this pair returns a corner solution fitted to one crash.
The buildable residue is a reporting and policy item, **owned by the app/portfolio lane**, and it
requires no new research. Re-open the optimiser only if a *genuinely* long-vol sleeve exists to
allocate to — which per K6 the current one is not.

---

## What none of these memos says

* **Not that these are bad ideas.** U4 is buildable and worth building; U6 is the most tradeable
  idea in the catalogue and is blocked on data, not on merit; U8's diagnosis is correct and only
  its prescribed method is unavailable.
* **Not that the U-series is closed.** After this session `U1`, `U2`, `U3`, `U5` and `U7` carry
  verdicts and `U4`, `U6`, `U8` carry design records. **A design record is not a measurement**,
  and anyone re-opening one of these three re-opens a live question, not a settled one.
* **Not that a convex overlay is a bad idea in general.** U3 measured *this* sleeve — 100% long
  calls at +0.37 delta — on *this* sample. A put sleeve or an index hedge is a different
  instrument and would need its own register.
