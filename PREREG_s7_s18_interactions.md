# PRE-REGISTRATION — S7 + S18: pre-registered interactions, and short interest as one

**One register, both items, committed before any arm has been scored.** Written after a premise
check against the code and the data (§1), reported in full because **one of the audit's four named
interactions cannot be built at all**, and **the other item's data does not reach half the panel**.

Both rows are `src=auto` — *"a lead, not a fact"*. S21, S16, S5 and S27 are the precedent: an
`auto` row has now four times proposed something already shipped or not buildable, and the only
reason that was caught each time is that the premise was checked against the code rather than
against the item text.

---

## 0. THE BASE RATE, STATED BEFORE ANY ARM RUNS

Two facts, both measured, both in the record:

1. **THE INTERACTION LITERATURE'S BASE RATE IS POOR.** Interaction terms in cross-sectional
   equity models are the canonical multiple-comparisons trap: the space is quadratic in the number
   of signals, the theory rarely pins the sign, and published interaction effects replicate badly.
   This register tests **only the audit's named list** and searches nothing beyond it — which is
   the single design choice that makes the exercise worth anything.
2. **EVERY COMBINATION-FLAVOURED ITEM THIS CATALOGUE HAS TESTED HAS BEEN REJECTED.** Not most —
   all of them: the **ML tree combiner** (rejected, and it *reversed* out of sample), **S20** rank
   composite, **S21** winsorisation (not replicated), **P6.4** consolidating momentum with
   institutional, **S3**'s three insider rebuilds, **S16**'s four issuance decompositions (one of
   them a rank identity), and **S5/S6/S13/S24/S27**'s five weighting schemes — where CPCV's own
   best challenger missed its bar by a factor of **79**.

**So the honest prior on every arm here is failure**, and §7 states it per arm. The reason to run
anyway: "we expect these to fail" is not a measurement, and the audit's own framing — *"the
resolution is not a bigger model, it is a smaller hypothesis"* — deserves the test it asks for.

---

## 1. PREMISE CHECK

**(a) `size × liquidity` IS NOT BUILDABLE, AND WILL NOT BE TESTED.** The audit's fourth named
interaction requires a liquidity measure. **There is none on this path.** The price export carries
**date and close only**, so `avg_dollar_volume` cannot be computed in the panel at all — this is
audit **B13**'s blocker, stated in the panel's own `prefilter_note` and re-verified today, and the
B13 ledger row was corrected last session from "IN PROGRESS" to **PARTIAL — BLOCKED ON DATA**
for exactly this reason. Wiring it needs SEP volume in the loader, which is a data-plumbing change
and a different item. **Reported as unbuildable, not silently replaced with a proxy** — a
market-cap or price-based stand-in would be a *different hypothesis* wearing the name of this one.
It charges **no trial**, on session 8's precedent that a test which cannot be run keeps the
denominator.

**(b) SHORT INTEREST DOES NOT REACH HALF THE PANEL, AND THE MEASURED NUMBER IS NOT THE AUDIT'S.**
The cache is real — `short_interest.pkl`, **48,539 tickers, 3,866,270 records**, settlement dates
**2018-01-27 → 2026-07-30**. The audit says coverage is *"40% of the panel dates"*. **Measured:
32 of 69 dates, 46.4%**, with the first covered date **2018-04-20** and per-date name coverage
running **88.1% → 98.6%** across the covered window.

**THE CONSEQUENCE IS STRUCTURAL AND DECIDES S18's DESIGN: every covered date is in the LATE
portion of the panel.** The panel runs 2009-01-15 → 2026-01-28 and nothing before 2018-04-20 has
data, so **S18 cannot satisfy a both-halves gate on the full panel — the early half has no
short-interest data at all.** This is not a power problem to be noted; it is an impossibility, and
§4.1 fixes what replaces it before any arm runs.

**(c) THE STANDALONE VERSION WAS ALREADY TESTED AND REJECTED, WHICH IS THE POINT OF S18.**
`neg_days_to_cover` (IC *t* +1.04) and `neg_short_interest_chg` (+0.42) were tested standalone
against a 2.0 bar and rejected. S18's thesis is that short interest is a **crowding** measure that
*conditions* other signals rather than predicting alone. This register tests that thesis and does
not re-test the standalone form.

**(d) `institutional accumulation` IS TESTED AS THE SHIPPED `institutional` THEME**, which is
`mean(z_inst_accum, z_sm_breadth)` — not the raw `inst_accum` column alone. Stated because it is a
substitution: the theme is the object the model actually carries, and using it keeps the arm on
the same footing as every other theme, but it is not literally the audit's phrase.

---

## 2. THE INSTRUMENT

**One panel — the banked corrected 69-date panel every published figure is measured on — and one
scoring per arm.** No rebuild: every input needed is already on it, and short interest joins from
the cache at analysis time.

**An interaction is ONE ADDED COLUMN, exactly as the audit specifies:** `z(z_a × z_b)`, z-scored
per date, entering the composite as an eighth input at the same 0.125 weight as every theme, with
the shipped present-weight-mass renormalisation (audit B7).

**A CONSEQUENCE THAT MUST BE STATED, BECAUSE IT IS NOT THE INTERACTION'S DOING:** adding an eighth
input at 0.125 moves each existing theme's *relative* weight from 1/7 to 1/8. So every interaction
arm is a **compound change** — the new term plus a dilution of the seven. That is what *"weighted
like any other input"* means, it is the audit's own construction, and it is registered here so the
dilution is not later mistaken for the interaction's effect.

**The point-in-time market-volatility regime** for arm A2 is built from the panel's own
`bench_ret` series, using **only dates strictly before** the scoring date. No same-date value, per
B26's rule.

**BOOK-LEVEL VERDICTS ONLY.** No arm may be promoted on a per-signal or per-theme IC. That rule
has now been demonstrated six times (P6.3, X3, S20/S21, S3, S16, and the five-scheme family).

---

## 3. THE ARMS — six, from the named list only, nothing searched

**S7 (three of the audit's four; the fourth is §1a):**

* **A1 — `value × quality`.** The quality-adjusted-value hypothesis; the audit calls it the
  best-documented of the set.
* **A2 — `momentum × market-volatility regime`.** Momentum crashes are a volatility phenomenon.
  The regime is the trailing realised volatility of the benchmark across prior rebalance dates,
  standardised across dates; the interaction is `z(z_momentum × z_regime)`.
* **A3 — `value × institutional`.** Cheap names institutions are accumulating against cheap names
  they are leaving (§1d on the substitution).

**S18 (all three, all partial-sample per §1b):**

* **A4 — `value × short_interest`.**
* **A5 — `momentum × short_interest`.**
* **A6 — SHORT-INTEREST EXCLUSION**, in the sense of S10: drop the **top 5% most-shorted** names
  from the top decile and measure what happens to **drawdown** and alpha.

Short interest is joined **point-in-time**: the latest settlement date **strictly before** the
scoring date, never on or after it. `days_to_cover` is the measure; a name with no settlement on
or before the scoring date is **absent, never imputed** — imputing a neutral value would convert
an availability gap into a signal, which is S10's failure mode.

---

## 4. THE GATE

Primary: the shipped margins — **≥ +100 bps top-decile alpha AND ≥ +0.25 long-short *t*, in BOTH
halves, boundary embargoed** — the same bar used by `SECTOR-NEUTRAL-B6`, `S20`, `S21`, `S3`, `S16`
and the five-scheme family. Verdict per arm: **ADOPT-ELIGIBLE** iff it clears both margins in both
halves; otherwise **REJECTED**; ambiguous is a **NULL** (`RUN_RULES` A6).

### 4.1 S18's halves are NOT the panel's halves, and that is fixed here

Because no short-interest data exists before 2018-04-20 (§1b), **A4–A6 are gated on the two halves
of the COVERED SUBSAMPLE — 32 dates, 16 per half — not on the panel's halves.**

**This is a materially weaker test and is labelled as such wherever it is quoted.** Sixteen dates
per half is exactly `holdout_compare_panels`' `min_dates=16` floor: the thinnest split the shipped
gate will accept. **A pass on 16-date halves is not the same object as a pass on 34-date halves**,
and no S18 result may be compared directly with an S7 one.

### 4.2 Bonferroni, and why it is not applied as the audit writes it

The audit prescribes *"Bonferroni across the number of interactions tested — with four
interactions the effective bar is p < 0.0125."* **That prescription assumes a p-value gate, and
this project's gate is a MARGIN gate** — a fixed alpha and *t* improvement in both halves, whose
floors X7 calibrated against a placebo. **Converting one into the other would be inventing a
correspondence that has never been calibrated**, which is the error X3 and session 10 both paid
for.

So: the shipped margin gate is primary and unadjusted, **and the multiplicity concern is honoured
the way the five-scheme register honoured it** — by labelling. **Any arm that clears is recorded
`ELIGIBLE — UNREPLICATED, 1 OF 6 SIBLING ARMS`, never "adopted"**, and that label travels with the
figure. Six arms against one bar make at-least-one-clears roughly a **26%** event under
independence; the arms are positively correlated, so that is an upper bound, but it is the right
order of magnitude.

### 4.3 The exclusion arm's two limits, from S10

A6 is an exclusion arm and inherits both of S10's hard-won caveats verbatim:

* **`max_drawdown` IS NEGATIVE.** An arm improves it by being **less** negative and the gain is
  **`arm − base`**. S10 shipped this backwards once and reported a 2.61pp worsening as a 2.61pp
  improvement. Pinned by a test.
* **X7 CALIBRATES NO DRAWDOWN FLOOR ANYWHERE**, so any drawdown change A6 produces is a
  **measurement carrying no verdict**, and S10 additionally measured that this book's worst
  drawdown spans a **single quarter** (COVID 2020Q1) — which the covered window contains.

---

## 5. CONTROLS — all read BEFORE any arm's verdict

* **C1 — the harness reproduces the published record** (alpha 0.07174142332098163, LS *t*
  2.8360640685320595, HAC 2.6199121240414884, monotonicity −0.8909090909090909). **The run ABORTS
  before any arm is read if it does not.**
* **C2 — identical rows** across arms; the S18 arms additionally share one covered-subsample row
  set with each other.
* **C3 — no arm is inert.** Within-date rank correlation against the deployed composite.
* **C4 — COVERAGE FIRST, per the COVERAGE RULE.** Every arm's non-null coverage is reported before
  its verdict, and the S18 arms' per-date name coverage is reported separately from their date
  coverage, because the two fail differently.
* **C5 — the short-interest join is POINT-IN-TIME.** Asserted directly: no joined settlement date
  may be on or after its scoring date. A look-ahead here would manufacture exactly the crowding
  effect the arms test for.
* **C6 — the interaction columns are genuinely interactions**, not proxies for one leg: each
  arm's added column is reported with its correlation to both parents. **A column correlating
  ~1.0 with either parent is that parent, and its arm is meaningless.**
* **C7 — the dilution is quantified.** The deployed composite is re-scored at 1/8 weights with a
  **constant** eighth column, isolating how much of any arm's movement is the dilution of §2
  rather than the interaction. Reported for every S7 arm.

---

## 6. WHAT ADOPTION WOULD COST

Adoption of any arm is a **VINTAGE EVENT** — it changes the composite users receive. The current
vintage is **DERIVED, never assumed** (`PT-GAPDUE`) at run time and recorded in the write-up.
**No arm is adopted by this register**; an eligible arm is recorded ELIGIBLE with the §4.2 label,
and the decision is Don's.

---

## 7. EXPECTATIONS, per arm, before any arm was scored

Framed by §0. **All six are expected to fail.**

1. **A1 `value × quality` fails — 75/25.** The best-documented of the set and therefore the most
   likely to be already priced; and both parents are already in the composite at full weight, so
   the interaction must add something *beyond* their sum.
2. **A2 `momentum × vol regime` fails — 80/20.** This is factor timing in a thin disguise, and
   **S6** — timing themes on their own trailing returns — was rejected days ago with a sign flip
   between halves.
3. **A3 `value × institutional` fails — 80/20**, and it carries an extra handicap the others do
   not: `institutional` has the panel's **worst coverage at 71.7%**, so the interaction is missing
   on nearly three rows in ten.
4. **A4 / A5 short-interest interactions fail — 85/15**, the highest confidence of the six. The
   standalone version was already rejected, the crowding thesis is a genuine hypothesis but a weak
   one, and **the test has 16-date halves**, which is close to no power at all.
5. **A6 the exclusion improves drawdown by less than S10's uncalibrated 2.0pp bar — 70/30.** S10
   found its own exclusion made drawdown **worse**, and measured that this book's drawdown is
   decided by a single quarter that an exclusion screen cannot dodge.
6. **At least one of the six clears in at least one half — 60/40.** A statement about noise across
   six correlated arms, not about an effect; §4.2 is the clause that keeps it from being read as
   one.
7. **The dilution control C7 accounts for a non-trivial share of any arm's alpha movement —
   65/35.** If true, it means the arms are partly measuring "seven themes at 1/8" rather than the
   interaction, and the register wants that separable.

---

## 8. TRIAL COST

**Six arms: equity `N` 170 → 176.** Charged whatever the verdicts are. **`size × liquidity`
charges nothing** — it cannot be run (§1a). The premise checks and the C7 dilution control charge
nothing; they measure what the code and data already are.

`BACKTEST_RESULTS.json` is re-run **from a clean tree** so the artifact carries the honest
denominator.

---

## 9. WHAT THIS REGISTER DOES NOT DO

* It does **not** search beyond the audit's named list. No additional interaction is tested,
  reported or mentioned as promising — searching the quadratic space is the exact failure the
  tree combiner already demonstrated.
* It does **not** re-test short interest standalone (§1c).
* It does **not** build a liquidity proxy to rescue `size × liquidity` (§1a).
* It does **not** change any live weight, and it does not touch `low_risk`, whose removal the
  volatility-regime arm might be read as complementing.
