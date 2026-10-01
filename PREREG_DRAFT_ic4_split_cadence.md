# PREREG DRAFT — IC4, SPLIT CADENCE: REFRESH THE THEMES AT THE RATES THEY DECAY AT

**DRAFT. Frontier Scout. No measurement, no arm, ZERO trials.** Ranked **4 of 6**.

**Seed idea (5), KEPT but re-engineered, and the re-engineering is the contribution.** The seed
asks for *"momentum refreshed faster inside a book whose value and quality refresh annually"* and
asks what panel that needs. **Answer: speeding momentum up needs a MONTHLY panel, which `MA33`
priced and which carries a hidden recalibration cost. Slowing value and quality DOWN creates the
same differential on the EXISTING 69-date quarterly panel with no rebuild at all.** The hypothesis
is about *relative* refresh rates, so it can be approached from either side, and only one side is
free.

---

## 1. MECHANISM

The seven weighted themes decay at very different rates, so refreshing them all on one clock
either re-reads slow themes that have not moved (paying turnover for noise) or lets fast themes go
stale between rebalances. Refresh each at a rate matched to its own persistence.

**ARM — ONE arm, the slow side: hold `value` and `quality` at their most recent ANNUAL reading
while `momentum`, `institutional` and `insider` refresh every quarter as now.** `size` and
`capital_discipline` also refresh annually, because they are the two most persistent themes and
annual is nearer their own rate. One arm, one pre-committed assignment of themes to clocks,
derived from `S22`'s measured persistence and **not swept**.

**The fast-side variant is NAMED AND DECLINED, with its cost**: refreshing momentum monthly needs
a monthly panel. `MA33` measured that as feasible (`bulk.prepare_daily` already down-samples to
one row per ticker-month, so monthly is the native granularity) at **~3× the 69-date build's ~20
minutes on every build thereafter** — but the binding cost is not the build. **Every `X7`
calibrated bar becomes an EXTRAPOLATION on a monthly panel** (2.7072 theme IC, 2.056680 LS-HAC,
1.826210 alpha-HAC, 19.667% PBO are calibrated for THIS panel and 69 dates), so it needs its own
placebo sweep of roughly **5–7 hours** before it can carry any verdict — a cost `MA33` records as
absent from the audit's own estimate. **And it inherits `S8`'s `prepare_daily` defect at a worse
ratio: the point-in-time market cap can be up to 31 days stale, which is a precision defect on a
quarterly panel and a THIRD OF THE REBALANCE INTERVAL on a monthly one.** The slow-side arm avoids
all of it.

## 2. THE RECORD'S EVIDENCE *FOR*

* **`S22` measured the per-theme persistence spread and it is 8.4×.** Per-name rank
  autocorrelation at one quarter: `size` **0.9915**, `capital_discipline` **0.8882**, `value`
  **0.6981**, `quality` **0.6786**, `momentum` **0.6414**, `insider` **0.3152**, `institutional`
  **0.1181**. **That is the mechanism, measured, not assumed** — `size` barely moves between
  quarters while `institutional` is almost entirely new each time. Refreshing both on one clock is
  demonstrably mismatched to the data.
* **13F's own decay independently supports the split from the other direction**: peaks Q−1, alive
  Q−2 (*t* 1.36), **dead Q−3** (*t* −0.04). A theme with a two-quarter half-life and a theme with
  a 0.99 autocorrelation should not share a refresh rate.
* **`S22`'s headline makes the slow side plausible rather than reckless**: top-decile alpha is
  **essentially flat from three months to two years** (+6.59% → +5.10% annualised, alpha HAC *t*
  never below 3.16), and median rank IC **rises** with horizon (+0.034 → ~+0.072). So a slower
  read of the slow themes is not obviously throwing information away.
* **The grid cost is already paid.** No rebuild, no new placebo sweep, no purchase.

## 3. THE RECORD'S EVIDENCE *AGAINST*

* **`S11` is the nearest precedent and it was REJECTED by the widest margin of its batch.** The
  horizon ensemble gave up **−4.22pp / −2.05pp** of alpha (Δ*t* −2.353 / −0.927) and its long-short
  leg moved against it exactly as pre-registered. **The distinction this draft rests on: `S11`
  blended two composites built at two HORIZONS, which `S22` had already shown share most of their
  information (the two horizons' weight vectors correlate +0.9013 and +0.9674, so the ensemble was
  largely one composite twice). This arm changes the REFRESH RATE of individual themes inside one
  composite at one horizon, which is a different object.** That claim is checkable and the register
  must state it in §1, not defend it later.
* **`S11`'s confound is a live warning for this arm too.** Its deviation from the deployed
  composite came mostly from *using IC-proportional weights at all* rather than from blending —
  i.e. the intervention was not what the register thought it was. **A split-cadence arm must hold
  the WEIGHTS exactly at the deployed flat 1/7 and change only the refresh clock**, or it will
  measure the same confound.
* **`P6`'s standing rule cuts against the motivation.** A theme's IC does not predict its marginal
  contribution to the composite — `X3` is the sharp form: `size` has the **worst** theme IC
  (**−0.30**) and carries the composite's **entire** statistical significance (adding it last takes
  alpha +4.10% → +7.17% and LS *t* 1.02 → 2.84). **So persistence, like IC, is a per-theme
  property and may not predict what happens to the blend** — exactly the inference `X3` exists to
  forbid. This is the strongest argument against and it belongs in the register's own §3.
* **`S8`/`S9` found no freshness gradient** at all on the fundamental axis, which is the axis
  `value` and `quality` live on. If fundamental staleness is free, slowing them costs nothing —
  but equally, it gains nothing, and the arm's upside then rests entirely on turnover.
* **Five weighting-family arms (`S5`, `S6`, `S13`, `S24`, `S27`) were all rejected**, and CPCV's
  best challenger missed by a factor of **79**. The prior on "re-arrange how the composite is
  assembled" is poor and measured.

## 4. BAR AND MDE

Gate: the shipped `holdout_compare_panels`, verbatim, both halves, both weightings, deployed flat
1/7 held fixed.

**MDE.** Paired within-panel → **no calibrated floor** (`V2G`, `R1-VAR`); the arm measures its
**own** paired HAC SE (`MB8`). Equity N **248**, hurdle **3.3206712** (derived). Holding four of
seven themes for four quarters is a **large** perturbation, nearer `V2G`'s whole-theme swap
(**0.9354pp**) than `MB8`'s haircut (**0.1106pp**), so the honest prior is an 80%-power MDE around
**2.6pp** at crit 2.0 (UNCALIBRATED) and **3.9pp** at the hurdle. **`S11`'s measured effect was
−4.22pp / −2.05pp, so a comparable effect IS resolvable at the full-sample end and marginal on the
late half — the register must print this before scoring.**

## 5. KILLS, FREE AND READ FIRST

* **K1 (FREE).** The theme-to-clock assignment must be **derived from `S22`'s banked persistence
  table and reproduce it**, not retyped. If the persistence ordering has moved, the assignment
  moves with it and the register is re-derived rather than kept.
* **K2 (FREE).** The annual clock must actually bite: the share of rows whose `value`/`quality`
  z-score differs from the quarterly reading must exceed a pre-committed floor. An inert arm
  closes at zero trials.
* **K3 (FREE).** Weight fidelity — the arm must reproduce the published record when the clock is
  set to quarterly for every theme (`top_decile_alpha` **0.07174142332098163**, LS naive *t*
  **2.8360640685320595**, HAC *t* **2.6199121240414884**, monotonicity **−0.8909090909090909**),
  at max |Δ| **0.000e+00**. **ABORT if not** — this is the control `MA28`'s C1 caught on its own
  first run and `W-1`'s K4 caught on its, in both cases because nine themes were scored at a
  seven-theme weight.
* **K4.** No look-ahead: an annual reading may only use a vintage strictly before the rebalance
  date. Pinned by test on a synthetic panel.

## 6. VINTAGE CONSEQUENCE

**On adoption: a VINTAGE EVENT**, and the most invasive of the six — it changes how the live
composite is assembled. Derive the vintage from `track_meter.VINTAGES`, never quote it; derived
today, **vintage 4 OPEN since 2026-08-13**, ~48 days accrued. Rule 6: the reset buys nothing
statistically. **ELIGIBLE, NOT ADOPTED**, routed to Don.

## 7. CAN OWNED DATA TEST IT?

**The slow-side arm: YES, on the existing 69-date panel, with no rebuild, no purchase and no new
placebo sweep.** The panel already carries every theme at every date; holding four of them at their
most recent annual reading is a scoring change, not a data change.

**The fast-side arm: NO, not without a monthly panel AND its own ~5–7 hour placebo recalibration**,
per `MA33`. It is named here so a successor does not rediscover the cost, and it is **declined**.
