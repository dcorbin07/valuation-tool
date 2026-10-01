# PREREG DRAFT — IC7, WHAT RENORMALISATION DOES TO A NAME WITH A COVERAGE HOLE

**DRAFT. Frontier Scout. No measurement, no arm, ZERO trials.** Ranked **2 of 6** for expected
value per trial. **This is the Scout's own item, not a seed**, and it is the strongest thing found
outside the seed list.

---

## 1. MECHANISM

`composite_from_frame` **renormalises by the present-weight mass** — the `B7`/`G` convention, and
the one SELECTION has always used, which is why the deployed weights were chosen under it. So a
name missing a theme is scored on the themes it has, each carrying a **larger** share of the mass.

**`institutional` has 71.7% coverage and `insider` 83.1%.** Therefore roughly **28% of panel rows
are scored on a composite in which `institutional` does not appear**, with the other six themes
up-weighted from 1/7 to 1/6 of the mass — while the other 72% are scored on the seven-theme
composite. **Two different composites are being compared to each other inside one ranking, and
which one a name gets is decided by whether a 13F filer happened to report it.**

**ARM: ONE arm. Impute a missing weighted theme at the date's own cross-sectional median (z = 0)
instead of renormalising**, so every name is scored on seven themes at identical weight mass. The
ranking then differs from the incumbent only where coverage differs — which is exactly the
exposure under test. One arm, no grid, no weight change: the deployed flat 1/7 is held fixed.

## 2. THE RECORD'S EVIDENCE *FOR*

* **`W-28` established the identity at the THEME level and it transfers exactly one level up.**
  The value theme is `df[cols].mean(axis=1)` and **pandas skips NaN**, so a row missing one input
  averages three instead of four — which `W-28` showed is *"demonstrably IDENTICAL to the theme
  with `book_to_price` DROPPED, which is `S1`'s REMOVAL arm, which `S1` measured as making the
  composite WORSE (−0.207 / −0.079 *t*)."* **The composite's renormalisation is the same
  construction one level up, and nobody has measured it there.** `W-28`'s own fix was to fall back
  to the incumbent column so the paired difference is exactly zero where the new one is absent —
  this arm applies that principle to themes.
* **The exposure is measured, not assumed**: `institutional` **71.7%**, `insider` **83.1%**, and
  `institutional` is **empty before 2013-06-30** — so the affected set is large and also
  **era-structured**, which means the incumbent convention makes the early panel a six-theme book
  and the late panel a seven-theme one.
* **`institutional` is not a dead theme**, so the up-weighting is not harmless: theme IC *t*
  **+1.55**, and `V2G`'s exploratory leave-one-out found dropping it is **the only one negative in
  both halves** (−1.41% full), which is why `V2G` named 13F *"the source to build first"*.
* **`S8`'s common-mode-versus-cross-sectional distinction is what makes this resolvable.** `S8`
  killed the 13F *staleness* lever because staleness is common across names (1.25 distinct values
  per date) and so **cannot re-rank**. **Coverage is the opposite: it varies name by name within a
  date, so it CAN re-rank** — and a cross-sectional exposure is the kind this gate can see.

## 3. THE RECORD'S EVIDENCE *AGAINST*

* **`V2G` is the nearest measurement and it came back IMMATERIAL** — the live four-theme book costs
  **−1.3133pp/yr** against the deployed seven-theme one, paired HAC *t* **−1.4040**, and the design
  resolves **1.8708pp** at |*t*| = 2 with **55% power** against a true 1.95pp gap. So the record's
  one reading of "what does renormalisation cost" could not separate it from zero.
  **THE MATERIAL DIFFERENCE, and the register must rest on it:** `V2G` removed three themes
  **UNIFORMLY, for every name** — and it proved the restricted arm IS the live book at max |dev|
  **0.000e+00** across all 113,945 rows precisely *because* renormalisation makes a uniform absence
  a clean re-weighting. **A uniform absence cannot re-rank the cross-section; every name loses the
  same theme.** This arm is about a **name-varying** absence, which can. `V2G` measured the level
  effect of renormalisation and is silent on its cross-sectional effect.
* **`MC10`'s arithmetic is the warning.** A mechanical re-cut of the same panel was shown to be
  unanswerable at the hurdle — 80% MDE **≥ 1.01pp** against a **0.83pp** gross ceiling. This arm
  must compute its own ceiling the same way, **before** running.
* **Imputing z = 0 is a choice and it is not neutral.** It assigns the cross-sectional median to a
  name about which nothing is known, which is a mild shrink toward the middle. `SECTOR-NEUTRAL-B6`
  measured the sharper version of this trap: both engine sector dicts **fail open**, so blanking an
  unknown *"does not abstain — it hands the row the middle of a 2.70x range."* **The register must
  state that imputation is an assumption, not a correction**, and report the arm's own abstention
  count rather than treating a filled cell as knowledge.
* **The deployed weights were selected under the incumbent convention** (`CLAUDE.md` `B7`/`G`), so
  changing it scores the shipped weights under a convention they were not chosen for. That is a
  real confound and it runs against the arm.
* **Five weighting-family arms were rejected** (`S5`, `S6`, `S13`, `S24`, `S27`), CPCV's best
  challenger missing by **79×**. Anything that changes how the composite is assembled inherits
  that prior.

## 4. BAR AND MDE

Gate: the shipped `holdout_compare_panels`, verbatim — **> +0.25** long-short *t* **AND > +100 bps**
top-decile alpha, **BOTH** halves, boundary embargoed, **BOTH** weightings, deployed flat 1/7 held
fixed.

**MDE.** Paired within-panel → **no calibrated floor** (`V2G`, `R1-VAR`); the arm measures its
**own** paired HAC SE (`MB8`, which forbids borrowing `V2G`'s 0.9354pp for a differently sized
perturbation). Equity N **248**, hurdle **3.3206712** (derived this session). The perturbation
touches ~28% of rows but moves each by at most the difference between a 1/6 and a 1/7 weighting of
one theme, so the honest prior is **well below `V2G`'s** and nearer `MB8`'s **0.1106pp** — an
80%-power MDE around **0.31pp** at crit 2.0 (**UNCALIBRATED**) and **0.46pp** at the hurdle.
**That is the one respect in which this arm is better posed than `V2G`: `V2G` could not resolve
1.87pp, and this arm should resolve a few tenths of a point — but the register must measure its own
SE and print it before scoring, not after.**

## 5. KILLS, FREE AND READ FIRST

* **K1 (FREE, zero trials). The exposure census, per date.** The share of rows missing at least one
  weighted theme, by date and by theme. If it is below a pre-committed floor the arm is inert and
  closes at zero trials; `institutional`'s 71.7% predicts it bites hard, and the register should
  state the expected ~28% in advance so a surprise is visible.
* **K2 (FREE). The era structure must be reported, not discovered.** `institutional` is empty
  before 2013-06-30, so the affected share is **not** stationary. If the arm's bite is
  concentrated in one half, the both-halves gate is measuring two different interventions and the
  register must say which.
* **K3 (FREE). The size costume.** Coverage correlates with size — a 13F filer reports large
  positions — so the imputed set is probably smaller-cap. Mean per-date |rho| between "has a
  coverage hole" and the `size` theme, against a pre-committed bar, reusing `R6`'s own **0.60**
  verbatim. **`U7`, `S10` and `R6` were each decided by this exact failure mode**, and an arm that
  is a size sort in disguise must withdraw rather than be scored.
* **K4. Fidelity, and ABORT on failure.** With imputation disabled the arm must reproduce the
  published record at max |Δ| **0.000e+00** — `top_decile_alpha` **0.07174142332098163**, LS naive
  *t* **2.8360640685320595**, HAC *t* **2.6199121240414884**, monotonicity
  **−0.8909090909090909**. This is the control `MA28`'s C1 and `W-1`'s K4 both caught on their
  first runs, in both cases from scoring nine themes at a seven-theme weight.
* **K5 (FREE).** No look-ahead: imputation uses the date's **own** cross-section and nothing later.
  Pinned by test with a positive control.

## 6. VINTAGE CONSEQUENCE

**On adoption: a VINTAGE EVENT** — it changes how every live score is assembled. Derive the
vintage from `track_meter.VINTAGES`, never quote it; derived today, **vintage 4, OPEN, opened
2026-08-13** (the S14 band at 0.30), ~48 days accrued. Rule 6: a reset discards the accrued clock
and buys nothing statistically, and the contract's meter has **13.3% power at 60 months**.
**ELIGIBLE, NOT ADOPTED**, routed to Don.

**One asymmetry worth naming for the adoption decision: this is a FIDELITY argument as much as an
alpha one.** Even a null is useful, because it would establish that the two-composites-in-one-
ranking exposure is immaterial — which is currently assumed rather than measured. `FIDELITY-2`
rebuilt `institutional` and `insider` to the panel's own definitions and cleared a +0.9190 /
+0.8726 fidelity bar, so **all seven themes now reach a live score**; whether the live path's
coverage holes match the panel's is a separate question this arm would also inform.

## 7. CAN OWNED DATA TEST IT?

**Yes — no purchase, no rebuild, no new placebo sweep.** The banked 69-date panel carries every
theme column with its holes intact, `composite_from_frame` is the one shipped composite, and all
five kills are free arithmetic on banked columns.
