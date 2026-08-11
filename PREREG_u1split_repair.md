# PRE-REGISTRATION — `U1-SPLIT`: repairing a corporate-action defect that moves a published headline

**Committed 2026-08-11, ALONE, before any repair code exists in the tree.** The defect was found
during U1's calibration (`e34dc9d`) and filed there; this document is the repair, and it is
written to the house rule that the moved figures and the expected direction are named **before**
anything is touched.

---

## 1. THE DEFECT, REPRODUCED INDEPENDENTLY

`options_backtest.simulate_trade` settles an untriggered contract at intrinsic against
`bars["raw_close"]` — deliberately the **unadjusted** close, with the comment *"as-traded:
strikes are not adjusted"*. That reasoning is correct **within** a split-free window and wrong
**across** one: at expiry the raw close is post-split while the strike is pre-split.

**GE, 1-for-8 reverse split, 2021-08-02.** Reproduced from the bars, not quoted from the row:

| date | `raw_close` | `adj_close` |
|---|---|---|
| 2021-07-30 | 12.9500 | 63.3710 |
| **2021-08-02** | **100.6000** | 61.5360 |
| 2021-09-17 (expiry) | 100.4700 | 61.4570 |

`12.95 × 8 = 103.60`, i.e. the post-split level — the adjusted series is continuous, the raw one
is not. The banked row is strike **14.00**, entry **0.2700**, exit **86.4700**, and
`max(0, 100.4700 − 14.00) = 86.4700` **to the cent**, so the settlement formula demonstrably ran
on mixed bases.

**The true value is not "unknowable" — it is zero.** On a 1-for-8 reverse split the OCC adjusts
the **deliverable** to `100/8 = 12.5` new shares and leaves the strike at 14.00, so quoted
intrinsic is `max(0, (12.5 × 100.47 − 100 × 14.00)/100) = 0.0000`.
**True P&L −100%. Booked P&L +31,921%.**

### The exposure is WIDER than the settlement line, and this changes the repair

Affected rows by exit reason:

| book | affected | target | stop | time_stop | expiry |
|---|---|---|---|---|---|
| R2 alert book | 15 / 3,885 | 6 | 4 | 2 | 3 |
| R2 control ×5 | 131 / 29,785 | 40 | 59 | 3 | 29 |
| U1 grid | 18 / 5,186 | 9 | 7 | 0 | 2 |

**Most affected rows never reach the settlement line.** They exit on target or stop — i.e. on
**post-split quotes**. For a *reverse* split the OCC keeps the strike, so
`theta_bulk.contract_history`, which matches on exact strike, happily returns post-split quotes
that refer to an adjusted deliverable. A "+100% target hit" on such a series is spurious.

**Therefore the repair must reject at ENTRY, on the contract life, not guard the settlement
line.** A settlement-only patch would leave the larger channel open.

---

## 2. THE REPAIR, FIXED NOW

**Reject a candidate trade when a split with ratio ≠ 1 falls in `(entry_date, expiry]`.**

* **Decided at entry, before the trade is simulated**, so it is provably **outcome-independent**.
  The tempting alternative — drop only trades whose *exit* lands after the split — is rejected:
  exit timing is determined by the outcome, so that rule would keep pre-split winners and drop
  expiry-runners, and expiry-running correlates with the payoff.
* Keyed on an **external table** (`data/bulk/prepared/actions.pkl`) and a **date comparison**,
  never on the size of a return.
* Implemented in `options_backtest.simulate_trade` behind an explicit `splits` argument that
  **defaults to None (no behaviour change when not supplied)**, and passed by the callers that
  build books. A rejected candidate is **counted** as `split_in_contract_life`, never silent.

### Exclusion, not re-pricing — and the choice is stated with its direction

Re-pricing is *possible* (§1 computes the true value for the flagship case) but needs OCC
adjustment logic per split type — forward splits divide the strike and multiply contracts,
reverse splits adjust the deliverable — applied to quote series that may or may not exist for
the adjusted contract. **That is a second opportunity to introduce a subtler defect while
repairing this one.**

**The direction is disclosed because it is not neutral.** The flagship case's true value is
**−100%**, so re-pricing would push the control's mean *further down* than excluding does, which
would help the alert *more*. **Exclusion is therefore the CONSERVATIVE choice with respect to
R2's standing negative verdict**, and that is why it is acceptable to take the cheaper repair.

### The banked books are re-banked by filtering, and that is exactly equivalent

The guard rejects a candidate **before** simulation and changes no surviving trade's arithmetic,
so removing the affected rows from a banked book yields **precisely** the book a re-mine with the
guard would produce. Re-mining ~34,000 trades to reach a set I can obtain by filtering would
spend hours to arrive at the same rows. **This equivalence is asserted here and will be verified
by re-mining a sample under the guard and checking the affected rows are absent and the surviving
rows bit-identical.**

**Originals are never overwritten.** Corrected books are written to new paths; both old and new
carry sha256 fingerprints in a manifest.

---

## 3. WHICH PUBLISHED FIGURES MOVE — NAMED BEFORE ANYTHING IS TOUCHED

Every figure below is quoted somewhere in `CLAUDE.md`, `HANDOFF_*.md` or a results artifact.
Each will be re-derived and corrected **in place, dated**, per the `CLAUDE.md` convention.

| # | published figure | where |
|---|---|---|
| P1 | R2 gap: real **+3.41%**/trade vs control **+10.06%**, gap **−6.65pp** | CLAUDE.md, HANDOFF_universe_backtest.md |
| P2 | R2 date-block CI95 **[−11.92pp, −2.13pp]** | CLAUDE.md |
| P3 | R2 paired sign-test **z −4.903**, 1,334 name-year cells | CLAUDE.md |
| P4 | R2 breadth: 133 new names **−0.47%**/trade (PF 0.988); 54 megacaps **+9.37%** | CLAUDE.md |
| P5 | O20 PIT-liquid **3,359 at +4.82%** vs illiquid **495 at −7.84%**, z **−3.475** | CLAUDE.md |
| P6 | R3 design effect **2.2121** vs shuffled-null p95 **1.2037** | CLAUDE.md |
| P7 | TP-BAR calibrated bar **+5.0812pp**; tp150 **+3.1948pp** (82nd pct); tp200 **+3.8238pp** (87th); shipped **+3.410308%**/trade | CLAUDE.md, HANDOFF_optionsbot.md, PREREG_A_take_profit_bar.md |
| P8 | U1's own figures | already split-clean — **must come back IDENTICAL**, and that is a control |

**P7 IS THE ONE THAT COULD CHANGE A VERDICT'S RELATIONSHIP TO ITS BAR.** TP-BAR rejected `tp150`
on C1 alone, by a margin of `+5.0812 − 3.1948 = 1.8864pp`. Both the bar and the gain are computed
on the same corpus this repair changes. **If the corrected gain crosses the corrected bar, item A
reopens and I will say so plainly.**

---

## 4. THE EXPECTATIONS, WRITTEN BEFORE ANY CORRECTED NUMBER EXISTS

| # | prediction | confidence |
|---|---|---|
| **D1** | R2's gap shrinks in magnitude to about **−5.06pp** and stays **negative and significant**; the verdict is UNCHANGED | 85/15 |
| **D2** | R2's date-block CI95 still **excludes zero on the negative side** | 80/20 |
| **D3** | R2's sign-test `z` shrinks in magnitude by **less than 0.5** and stays past −4 | 65/35 |
| **D4** | P4's breadth claim keeps its **sign** — the 133 new names stay ≤ 0 | 70/30 |
| **D5** | TP-BAR's bar and `tp150` gain each move by **less than 0.5pp**, and **`tp150` still FAILS C1** | 75/25 |
| **D6** | **No verdict anywhere flips** — not R2, not TP-BAR, not U1 | 75/25 |
| **D7** | The freeze manifest still verifies: `data/options/` is untouched, so **zero** symbol-year stamps move | 90/10 |

**D5 and D6 are the ones that matter.** They are also the ones I would most like to be true,
which is precisely why they are written down first.

---

## 5. TRIAL COST

**Zero.** A correctness repair searches nothing and tests no hypothesis: it re-derives figures
that already exist on a corpus that was always meant to be split-clean. Options `N` stays **210**,
equity `N` stays **149**. Re-deriving a published number after fixing a defect in it is not a new
trial, and charging one would create an incentive to leave defects unrepaired.


---

## 6. THE RESULT — repaired, re-derived, and **no verdict moves**

Run 2026-08-11. `data/options_universe/U1SPLIT_REDERIVATION.json`,
`data/options_universe/U1SPLIT_MANIFEST.json`, `data/options_pathstudy/U1SPLIT_TPBAR.json`.
Reproduce with `python -m scripts.u1split_rebank` and `python -m scripts.u1split_tpbar`.

### The control that makes the correction checkable

**Every `as_published` figure reproduces the record to the digit** before any corrected number is
quoted: gap **-6.6468pp**, date-block CI95 **[-11.9152, -2.1317]**, sign-test z **-4.9027** over
**1,334** cells, breadth **+9.3720%** / **-0.4713%**, design effect **2.2121** vs null p95
**1.2037**, and TP-BAR's bar **+5.0812pp** with `tp150` **+3.1948pp** at the **82nd** percentile
and shipped **+3.410308%**/trade. A re-derivation that could not reproduce the old numbers would
be evidence about the harness, not about the defect.

### P1-P3 — the R2 headline

| | as published | **split-clean** |
|---|---|---|
| alert book | +3.4103% (n 3,885) | **+3.2702%** (n 3,870) |
| five-seed control | +10.0571% (n 29,785) | **+8.3342%** (n 29,654) |
| **gap** | **-6.6468pp** | **-5.0640pp** |
| date-block CI95 | [-11.9152, -2.1317]pp | **[-8.5957, -1.5325]pp** |
| sign test | -4.9027, 577/1,334 (43.3%) | **-4.9612, 575/1,332 (43.2%), p 7e-07** |

**24% of the published gap was a corporate-action artifact.** The control is contaminated ~12x
harder (131 rows vs 15) because it draws many random days per name-year, so **the defect was
making R2's negative verdict look worse than it is.**

**REPORTED BECAUSE IT CUTS AGAINST THE OBVIOUS READING: the sign test does not weaken, it
STRENGTHENS**, -4.9027 -> -4.9612. The mean gap shrank because the artifact lived in the
control's right tail; the median name-year cell never depended on it. **That is also why D3 was
wrong.**

### P4-P6

* **Breadth** — baseline 54 megacaps **+9.1391%**, new names **-0.5589%**. Sign preserved; the
  claim's substance is unchanged. **The count is 132 names, not the 133 `CLAUDE.md` has said** —
  `UNIVERSE_RESULTS.json` has always read 132.
* **O20** — liquid **3,347 at +4.7293%**, illiquid **494 at -8.0168%**. Means move by hundredths.
* **R3** — design effect **2.1837** vs shuffled null p95 **1.1898**; clustering still measurable,
  haircut 1.478x rather than 1.487x.

**P5's `z -3.475` DID NOT REPRODUCE AND IS NOT RESTATED.** The same construction that reproduces
every other O20 figure gives **-4.8953** as published. The figure is in no shipped artifact, so
it cannot be reconciled from the repository. **The discrepancy is recorded rather than papered
over with a number that merely agrees in direction** — that is how the 1.85 design effect
travelled out of scope. **Owner: the O20 lane.** O20's direction holds on every construction.

### P7 — the one that could have reopened item A. **IT DOES NOT.**

| | as published | **split-clean** |
|---|---|---|
| C1 bar (p95) | +5.0812pp | **+5.1302pp** |
| `tp150` gain | +3.1948pp (82nd pct) | **+3.1834pp (81st)** |
| `tp200` gain | +3.8238pp (87th pct) | **+3.8653pp (87th)** |
| shipped | +3.410308%/trade | **+3.270181%** |
| draws beating shipped | 53/100 | **54/100** |

**Both arms still FAIL C1, and the margin WIDENS** — `tp150`'s shortfall goes 1.8864pp ->
1.9468pp. **Item A stays closed; TP-BAR's verdict is unchanged.** The bar moved *up* and the gain
moved *down*, i.e. both against the arm, which is the opposite of the direction a repair would
need to run to rescue it.

### Fingerprints re-stamped

* **The freeze is untouched and that was verified, not asserted: 1,429 symbol-years checked,
  0 changed.** This repair never writes to `data/options/`, so every banked replay pin still
  holds and no frozen result becomes unreplayable.
* Corrected books are **new files** — `state_r2_splitclean.pkl`,
  `control_r2_splitclean_seed{0..4}.pkl`. **Originals are never overwritten**; they are the
  record of what was published and are needed to check this very correction.
  `U1SPLIT_MANIFEST.json` carries sha256 of **both** sides of all six books plus the freeze
  manifest.

### Equivalence, verified rather than assumed

Re-mining the 2021-07-22 rebalance **under the guard** produced **146** trades against **147**
banked; the dropped row was **GE**; the key sets matched exactly and **0 of 146 shared trades
differed on any field**. That is what licenses re-banking ~34,000 trades by filter instead of a
multi-hour re-mine.

### The live product was quoting the wrong figure, and a test caught the change

`valuation/web/payoff.py` renders the R2 gap to **users**, and `tests/test_payoff.py` pins the
exact string with the message *"the measured R2 gap must be quoted, not gestured at"*. Correcting
the copy broke that test — **which is the test working**, not an obstacle.

**The pin was UPDATED, never loosened.** A test that stopped naming a number would stop enforcing
the property it exists for. The figure now lives in ONE constant, `payoff.R2_GAP_PP = -5.06`,
which the rendered sentence interpolates and the test asserts against **both** the constant and
the literal — so the number a user reads and the number a test pins cannot drift apart, and
neither can move alone.

### A defect in the repair, found by the repair's own check

The guard's rejections were being counted as `no_trade` — `u1_entry._mine_cell` collapsed every
simulation failure to one label — so the guard worked but **could not be seen working**, against
this register's own promise that rejections would be "counted, never silent". Found by the
equivalence check, not by reading the code. Fixed; the counter now reads
`split_in_contract_life: 1`, and a test pins it.

### The expectations, scored: **6 right, 1 wrong**

| | prediction | outcome |
|---|---|---|
| D1 | gap ~ -5.06pp, still negative and significant, verdict unchanged | **RIGHT** |
| D2 | date-block CI95 still excludes zero on the negative side | **RIGHT** |
| D3 | sign-test z *shrinks* in magnitude by < 0.5, stays past -4 | **WRONG** — it *grew*, -4.9027 -> -4.9612. Right about the size of the move (0.0585), wrong about its sign |
| D4 | breadth keeps its sign | **RIGHT** — new names -0.5589% |
| D5 | TP-BAR's bar and `tp150` each move < 0.5pp; `tp150` still fails | **RIGHT** — 0.0490 and 0.0114 |
| D6 | no verdict anywhere flips | **RIGHT** |
| D7 | freeze verifies, zero symbol-years move | **RIGHT** — 1,429 checked, 0 changed |

**D3 is the instructive miss**: it assumed a correction that shrinks a mean must weaken the
statistic built on it. The two are different objects — one is a tail average, the other a count
of cell wins — and the artifact only ever lived in the tail.

### Trial cost

**Zero, as committed.** Options `N` stays **210**, equity **149**. **No research-log row is
added**: the log is one row per pre-registered *test*, and this is a correctness repair that
tested no hypothesis. It is recorded in `VALQUO_LEDGER.md` instead.
