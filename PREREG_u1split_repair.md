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
