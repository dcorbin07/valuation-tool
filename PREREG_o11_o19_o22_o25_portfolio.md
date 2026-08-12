# PRE-REGISTRATION — O11 + O19 + O22 + O25, the portfolio-and-capacity batch

**One register, four items, nine arms, committed ALONE before any measurement code exists.**
Ledger rows `O11` (portfolio layer for single-leg), `O19` (cheap-contract sizing artefact), `O22`
(capacity-constrained replay) and `O25` (sell the wing after the move), all `OPEN`.

---

## §0 SCOPE FACTS, ALL MEASURED BEFORE THIS REGISTER WAS WRITTEN

No outcome, expectancy, equity curve or capacity number was computed first.

### §0.1 The ledger is wrong about ALL FOUR rows — the third session running

Every one of these four is marked **`src=auto`** with the note *"no mention anywhere in the
corpus"*. **All four are false.** `VALQUO_EDGE_AUDIT.md` carries full sections at **`:1066` (O11)**,
**`:1985` (O19)**, **`:2023` (O22)** and **`:2061` (O25)**, each specifying a method. **So every
definition below is QUOTED from the audit, not invented by me.**

This is now the **third consecutive session** in which that note has been wrong (session 29: O6,
O17; session 30 corrected both; this session: four more). **The `src=auto` note in this ledger is
not evidence of absence and should stop being read as such.** All four notes are corrected as part
of this item.

### §0.2 THIS DOES NOT CLOSE THE O-SERIES, AND THE CLAIM IS QUALIFIED HERE BEFORE IT CAN BE MADE

Counted from the ledger: the O-series holds **26 rows — 21 `DONE`, 4 `OPEN` (these), and `O14`**.
**`O14` is NOT closed by this batch and will still be open afterwards.** Its own note is explicit:
collection is complete and the first analysis landed (O10/O18 used the tick cache for
execution-cost questions), but *"the put/call and unusual-volume studies this cache was justified
by are still not done."*

**So the defensible sentence, fixed now so it cannot be inflated later, is: this batch closes the
last four OPEN audit HYPOTHESIS rows in the O-series, leaving `O14` open as a data-collection row
whose justifying analyses remain untested.** It is **not** "the O-series is closed".

### §0.3 O11 is fully computable from the FREEZE — no re-mine

`simulate_book` strikes equity daily, so it needs a mark path per trade. **Measured on 120 randomly
sampled banked trades: the tracked contract is found in the corrected freeze on 120 of 120, with a
median of 40 mark-days, a 10th percentile of 34, and ZERO trades holding fewer mark-days than
`held_days`.** The freeze is therefore the mark source and no re-mine is needed.

### §0.4 O25 CANNOT use the freeze, and the substitution is disclosed rather than made quietly

O25 needs a **15-delta call in the same expiry on the crossing date**, i.e. a full chain on a date
the book did not enter. **Measured: the corrected freeze has 3,884 full-chain days and 3,869 of
them — 99.6% — are banked ENTRY dates.** This is O21's and O3's finding for the third time. **O25's
chains therefore come from the EOD cache** (`data/options/<TKR>/<TKR>-<YEAR>.pkl`); the freeze is
used for O11's marks only.

### §0.5 The portfolio layer exists and has genuinely never been applied to the arm that lived

The audit's claim was checked rather than repeated: `options_vrp_portfolio.simulate_book` is called
by **`optvrp_report.py` only**. `_exit_date_single_leg` exists but feeds `arm_correlation` — the
VRP-vs-single-leg monthly correlation — **not** the book simulation. The audit is right.

## §1 EXECUTION ORDER — PRE-COMMITTED, AND MECHANICALLY ENFORCED

**`O19` RUNS FIRST, IN ITS OWN PASS, AND IS WRITTEN AND READ BEFORE ANY `O11` NUMBER EXISTS.**

This is the direct repair of session 26's own process defect, where O10's gating control `C2` and
its outcome statistics were computed in the same pass, so it could not be claimed the control was
read first. Here the ordering is **not a promise, it is a mechanism**:

1. `--stage o19` runs alone and writes `O19_SIZING_ARTEFACT.json`.
2. `--stage o11` **refuses to run** unless that artifact already exists, **reads its verdict, and
   embeds it verbatim** in its own payload.

**Why the order matters and is not ceremony.** O19 asks whether the book's measured expectancy is
an artefact of whole-contract arithmetic putting the largest *contract counts* on the cheapest
options. O11's equity curve is built by sizing in **whole contracts**, so it *inherits* whatever
O19 finds. Reading O11 first would mean interpreting an equity curve without knowing whether its
own sizing rule is the thing generating the number.

## §2 THE SPLIT-ADJUSTED-SPOT GUARD — MANDATORY, AT CONSTRUCTION

Session 30 found the U1-SPLIT defect class recurring: option strikes are **as-traded**, the bars
cache's `close` is **split- and dividend-adjusted** (NVDA 2012 reads 0.27 against a raw 11.97), and
matching one against the other **fails silently**. It has now appeared twice.

**A shared guard `assert_raw_spot` is built into this register's module and is called by every
instrument here that touches a price.** It compares the price series against the book's own
`underlying_entry` and **raises** if the median relative error exceeds **1e-6** on the overlapping
dates. **It fails the run rather than warning**, because a warning nobody reads is how this defect
survived to a second appearance. Pinned by tests, including one that fails if the guard is ever
downgraded to a warning.

## §3 THE FOUR ITEMS — DEFINITIONS FIXED HERE

### §3.1 O19 — the sizing artefact (2 arms, runs FIRST)

The audit's method, quoted: *"Report expectancy three ways: equal-weighted per trade (current),
contract-weighted, and dollar-weighted. Then re-run with a minimum premium floor of $1.00 and $2.00
and see whether the edge concentrates in or away from cheap contracts."*

* **A1 — WEIGHTING.** Expectancy equal-weighted, contract-weighted (contracts from
  `RISK_PER_TRADE = $1,000` and whole contracts) and dollar-weighted.
* **A2 — PREMIUM FLOOR.** The same three, restricted to entry premium ≥ **$1.00** and ≥ **$2.00**.

**ARTEFACT** iff the equal-weighted and dollar-weighted expectancies differ in **sign**, or the
premium floor moves expectancy by more than **2.00pp** in either direction with month-block CI95
excluding zero. Otherwise **NOT-AN-ARTEFACT**. Both halves required for the floor arm.

### §3.2 O11 — the portfolio layer (4 arms)

Apply the **existing** `options_vrp_portfolio.simulate_book` to the single-leg book — imported, not
re-implemented, so this is the same arithmetic the VRP arm was judged by (B7's defect class).
Marks from the freeze. Report the equity curve, **max drawdown, longest drawdown duration, and
time to recovery**.

**FOUR CELLS, NAMED NOW, AND NO GRID IS SWEPT** — the in-search-to-holdout collapse
(+8.43%/yr → −0.04%/yr) is already paid for once:

| arm | initial capital | concurrency cap |
|---|---|---|
| **B1** | $50,000 | 10 |
| **B2** | $50,000 | 50 |
| **B3** | $250,000 | 10 |
| **B4** | $250,000 | 50 |

**Verdict per cell, on the pre-committed drawdown criterion** (O12's ruin framing, quoted rather
than re-derived): **UNSURVIVABLE** if max drawdown ≥ **50%** of peak equity; **SURVIVABLE** if
< **25%**; otherwise **MARGINAL**. Required in **both halves**.

### §3.3 O22 — capacity (1 arm)

**P1's equity method, ported.** Participation = position notional / depth, where **depth is the
contract's own `pit_atm_oi_notional`** (already banked, point-in-time). Modelled one-way cost rises
with participation on the same functional form P1 used, with **λ = 1.0 as the headline and λ ∈
{0.5, 2.0} reported as a band, not as separate trials** — P1's own treatment.

**CAPACITY = the AUM at which modelled one-way cost crosses the book's own gross per-trade edge.**
Reported as an **UPPER BOUND**, for P1's reason: depth comes from names that were mined, and mining
selected on liquidity.

### §3.4 O25 — sell the wing after the move (2 arms)

The audit's method, quoted: *"at each point where a position reaches +75% or +100%, test selling a
15-delta call in the same expiry instead of closing. Measure the resulting distribution against
both closing and holding."*

* **D1 — wing at +75%.** **D2 — wing at +100%.**

At the first mark where the position's mid crosses the threshold, sell the call in the same expiry
whose delta is nearest **0.15** (from the EOD chain, IV solved from that day's mid, `q = 0`,
`r = 0.03`), entering the short at the **BID** (aggression 1.0, as the book charges). Both legs run
to the banked exit date; the short is bought back at the **ASK**.

**Each arm is compared PAIRED against both comparators the audit names — CLOSING at the crossing
and HOLDING to the banked exit.** CANDIDATE iff the paired mean difference against **both**
comparators is positive with a month-block CI95 excluding zero, **in both halves**.

**THE RISK SIDE IS PRE-REGISTERED AS REPORTED-NOT-VERDICTED**, because the audit says the wing
*"will very likely reduce expectancy and improve consistency"* and that whether that is a good
trade depends on O12: share positive, standard deviation, and the tail share above +100% are
reported for every arm **without a verdict**, since this register fixes no threshold for them.

## §4 STATISTICS

Month-block bootstrap (R3's standing rule) for every interval; **a trade-level *t* is never
quoted**. 2,000 draws, seed **20260812**. Both halves split at the book's median entry date.
Paired differences are computed **within trade**, so market direction cancels.

## §5 DEAD-ENTRY FRAMING — FIXED BEFORE ANY RESULT

**R2 stands: the options entry signal loses to random entry by −5.0640pp and nothing here can
re-open it.**

* A CANDIDATE or a SURVIVABLE verdict here is about **construction** — sizing, capacity, exit
  shape — **on a book whose entry is dead.** It is a candidate for a **future** book, never
  evidence the alert works.
* **O22's capacity number is mechanical, not a recommendation.** It answers *"how much could this
  hold"*, never *"how much should be deployed"*, and it is stated with R2 attached.
* **Nothing is adopted whatever the result.** `RISK_PER_TRADE`, `DEFAULT_AGGRESSION`,
  `pick_contract` and every exit constant are untouched; a material result is **routed to Don**.

## §6 EXPECTATIONS — WRITTEN DOWN FIRST

| # | expectation | confidence |
|---|---|---|
| E1 | O19 returns NOT-AN-ARTEFACT — equal- and dollar-weighted agree in sign | 60/40 |
| E2 | A premium floor of $1.00 RAISES expectancy (the edge sits away from the cheapest contracts) | 55/45 |
| E3 | At least one O11 cell is UNSURVIVABLE (max drawdown ≥ 50%) | 70/30 |
| E4 | The $50k / concurrency-50 cell is the worst of the four | 65/35 |
| E5 | O22 capacity is under $10M — far below the equity book's $23M | 75/25 |
| E6 | Neither O25 arm is a CANDIDATE on expectancy | 80/20 |
| E7 | Both O25 arms reduce standard deviation and raise share-positive (the audit's own prediction) | 75/25 |
| E8 | Alerts cluster in time, so the concurrency cap binds hardest in the richest weeks (the audit's third possibility) | 60/40 |

## §7 TRIAL COST

**9 options trials: 2 (O19) + 4 (O11) + 1 (O22) + 2 (O25).** Options `N` **271 → 280.**
**Equity and infra `N` untouched.**

O19 is charged despite being called a diagnostic, because it carries a pre-committed decision rule
and could be reported as a finding in its own right. The λ band in O22, the risk-side statistics in
O25, and every control are charged **zero** — none carries a verdict.

## §8 VOID CONDITIONS

1. Fewer than **3,000** banked trades acquire a usable mark path for O11, or fewer than **200**
   threshold crossings for either O25 arm.
2. Any change after an outcome is read to: the four O11 cells, the drawdown thresholds, the O19
   decision rule or its premium floors, the depth measure or λ headline in O22, the 0.15 target
   delta or the two O25 thresholds, the seed, the draw count, or any verdict rule.
3. Running O11 before O19 has been written and read, or adding a fifth O11 cell after seeing the
   first four.
4. `assert_raw_spot` being downgraded from a raise to a warning, or bypassed for any instrument.
5. Quoting any arm as an adoption, as evidence about the options ENTRY signal, or as a
   recommendation to deploy capital.
6. Claiming this batch closes the O-series (see §0.2 — `O14` remains open).
