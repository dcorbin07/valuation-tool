# RISK_PRIMARY_MAP.md — the axis this project has never tested, and what it can bear
## Frontier Scout, 2026-08-24. Part 2 of the redraw commission.

**Discipline:** no outcome statistic on market data was computed anywhere in this file. Every
number below is either (a) already published in the record, or (b) **design arithmetic on
published summary statistics** — the same class as `MB13`'s 34.2-years table and `MB22`'s
required-n gate, which is the instrument this commission asks me to use. Correlation inputs
are **parameterised, not measured**: where a result depends on ρ I give the table and name
the measurement the register must make first.

**Counters:** equity ~242 (hurdle **3.3133**), options 305, infra ~20 — concurrent lanes are
moving these hourly; every bar below is quoted at 3.3133 and **re-read at run** (`MA37`).

---

## 0. THREE PREMISE CORRECTIONS FIRST — the gap is real, and it is not quite where the brief puts it

**(a) The project is not Sharpe-blind. It is Sharpe-blind AT THE REGISTER LEVEL.** The
**Deflated Sharpe Ratio** is a calibrated, trials-aware, risk-adjusted bar that has shipped
since `M1`/`B9`: floor **0.6637** against a statistic **0.7863** at `N` = 224, re-derived at
`ARTIFACT-N`, and marked **stale-by-construction** at every new `N` by `MB31` (`sr0` is a
direct function of `N`). So a Sharpe-shaped bar exists and gates the **headline**. What has
never happened is the thing the brief is really pointing at: **no register has ever made a
risk statistic its PRIMARY decision metric**, and `X7` calibrates no floor for one.

**(b) The machinery for reasoning about risk-adjusted detection already exists, ported and
validated.** `MB22`'s gate is expressed in **IR units** — TIDEMARK's charter table (IR 0.20 →
196, IR 0.30 → 87, IR 0.15 → 348 independent observations at crit 1.96) reproduces exactly.
That is a risk-adjusted power instrument sitting unused on this question. This file points it
at the question.

**(c) `S13` is worse than "judged on the wrong instrument" — its own row says the instrument
could not move.** The ledger records: *"it changes position sizing INSIDE the top decile and
leaves the composite alone, so the decile MEMBERSHIP is unchanged and the long-short leg is
unchanged BY CONSTRUCTION. Its t margin is therefore recorded N/A and may NEVER be
reported."* So `S13` was rejected on an **alpha gate its design was structurally incapable of
clearing**, while the statistic it was built to move (Sharpe 0.5866 → 0.6261, drawdown flat)
had no bar to clear at all. That is the cleanest instrument-mismatch in the record, and it is
the reason this family deserved a session.

---

## 1. THE ARITHMETIC — can a risk-primary gate be calibrated on 69 quarterly periods?

Two independent routes. **They agree, which is the strongest form this record accepts.**

### Route A — the project's own ported gate (the LEVEL question)

Panel: 69 quarterly periods, 17.3 years. `MB13`'s measured design effect **1.177** gives
`n_eff/n` = **0.850**, so **≈14.7 effective independent years**.

| target IR | required independent obs @ crit 1.96 | @ honest hurdle 3.3133 | panel has |
|---|---|---|---|
| 0.30 (a strong strategy) | **87** | **192** | **≈14.7** |
| 0.20 | 196 | 431 | ≈14.7 |
| 0.15 | 348 | 766 | ≈14.7 |

**The panel cannot resolve the LEVEL of an information ratio at any plausible value.** It is
short by a factor of 6 at the most generous bar and 13 at the honest one.

### Route B — the paired DIFFERENCE (the generous framing, and the one the family needs)

The level question is unfairly hard: an `S13`-class register compares two constructions on
**the same names over the same dates**, so the arms are enormously correlated and the paired
standard error is far smaller. This is the framing that gives the family its best shot.
Jobson–Korkie (1981) with Memmel's (2003) correction, for arms with correlation ρ:

`Var(ΔSR) = (1/n)·[ 2(1−ρ) + SR²(1−ρ²) ]`

At `n` = 69 quarterly, `SR_q` ≈ 0.293 (the published 0.5866 annualised), annualising the SE
by ×2:

| ρ | SE(ΔSR), annualised | MDE @ crit 2.0 (50% / 80%) | MDE @ hurdle 3.3133 (50% / 80%) |
|---|---|---|---|
| 0.90 | 0.1120 | 0.224 / 0.318 | 0.371 / 0.465 |
| 0.95 | 0.0793 | 0.159 / 0.225 | 0.263 / 0.329 |
| 0.97 | 0.0614 | 0.123 / 0.174 | **0.204 / 0.255** |
| 0.99 | 0.0355 | 0.071 / 0.101 | 0.118 / 0.147 |

**`S13`'s observed improvement was +0.0395.** At ρ = 0.97 the 80%-power threshold at the
honest hurdle is **6.5× larger than the effect**. At ρ = 0.99 — two books nearly identical —
it is still **3.7× larger**.

**Solve for the ρ that would make `S13`'s gain detectable** (80% power, honest hurdle):
**ρ ≥ 0.9993.**

### The paradox that kills the family, stated exactly

Power in a paired Sharpe test comes from ρ → 1. **But ΔSR itself vanishes as ρ → 1** — two
books correlated at 0.9993 are the same book, and there is nothing left to detect. The design
is self-defeating: *the pairing tight enough to see the effect is tight enough to abolish it.*
This is not a data-collection problem and no vendor sells the fix; it is a property of the
statistic on any sample this length.

### **VERDICT 1 — SHARPE-PRIMARY GATES ARE UNPOWERED-BY-CONSTRUCTION ON THIS PANEL. KILLED.**
Parked with its condition (the standing form): re-open only if the inputs change — materially
more independent periods (forward time at one quarter per quarter), or a statistic whose noise
is not dominated by the mean. **New data does not lift this; only new time does.**

### Drawdown — worse, and it takes one line

`S10` measured that this book's maximum peak-to-trough is **exactly one 63-day period on every
arm, COVID 2020Q1, trough index 44 of 69**. The sample size for "max drawdown" is therefore
**one event**. There is no standard error to form, no floor to calibrate, and a placebo-derived
floor would be measuring *how far a random book fell in one particular market crash* — a fact
about March 2020, not about any strategy.

### **VERDICT 2 — DRAWDOWN-PRIMARY GATES CANNOT EXIST HERE. KILLED, n = 1.**

**What CAN move drawdown, said honestly:** nothing at the name level (`S10` proved it — the
drawdown is market-wide). Only **book-level exposure**: hold less, hedge it, or lower beta.
All three reduce expected return roughly in proportion, which makes them a **preference Don
expresses**, not an edge a register discovers. Their honest home is the **utility class that
already exists** — `F-6`'s collar ledger and `F-20`'s storm-gated married puts, both of which
price insurance rather than claiming alpha. That is the correct answer to "what would a
drawdown-gated register look like": *it looks like a utility ledger, and we already built two.*

---

## 2. IS X7's PLACEBO MACHINERY RE-POINTABLE AT A RISK STATISTIC?

**Partly — and not for the question the family actually asks.** Three findings:

1. **For a single book ("is this Sharpe better than chance?") it is mechanically constructible
   and answers the wrong question.** Each placebo draw yields a book and every book has a
   Sharpe, so a p95 floor exists. But a placebo book has ≈0 alpha by construction, so its
   Sharpe is ≈0 and *any* positive Sharpe clears. That is a signal-existence test wearing risk
   clothing — and signal-existence is already answered by `R9`/`X3`. It adds nothing.
2. **For the DIFFERENCE of two constructions it is unsound, structurally.** `placebo_panel`
   permutes the signal away; with no signal, both arms of a weighting comparison collapse to
   the same random book, so the null contains **no construction contrast at all**. The null
   being generated is not the null being tested.
3. **`MB21`'s finding compounds it.** `placebo_panel` has **zero persistence** (measured
   −0.0016 / +0.0010 / +0.0016 across three seeds) against a real composite at **0.5677** at
   one quarter. A *variance* statistic computed on a memoryless placebo mis-states the
   volatility of a persistent, factor-tilted book — and volatility is the whole denominator.

**What IS sound, and it is cheaper than a placebo sweep:**

* **The weight-scramble null** (new, small): permute the *weight vector* within the top decile
  while preserving its concentration profile and holding membership fixed. That null contains
  exactly the contrast under test — "does THIS weighting beat an arbitrary one of the same
  shape?" — and destroys nothing else. This is the instrument the family needs, and it is one
  session of work.
* **For variance specifically, no placebo is needed at all.** The paired variance test
  (**Pitman–Morgan**, via `corr(x+y, x−y)`) has an analytic null; `X7`'s floors exist because
  alpha's null was unknown, and variance's is not. The project's conventions are still met by
  the date-block bootstrap (`R3`'s machinery, already shipped) plus the both-halves rule.

---

## 3. THE CONSTRUCTIVE SUCCESSOR — decompose the risk question into legs that can be seen

The reason Sharpe fails is precise and it points at the fix: **Sharpe's noise is dominated by
its numerator.** Mean returns are the hardest thing on this panel to estimate; variances are
among the easiest. So split the question:

* **Leg 1 — does the construction reduce VOLATILITY?** Highly powered (below).
* **Leg 2 — does it cost ALPHA?** The existing, calibrated instrument, run as
  **non-inferiority** (`MB8`'s registered shape, inverted).
* **Sharpe is then REPORTED as a derived quantity with its honest CI — and never decides.**

### The variance leg's power (paired log-variance ratio, `SE = √(4(1−ρ²)/n)`, n = 69)

| ρ | SE(ln σ²-ratio) | detectable vol reduction @ hurdle 3.3133 (50% / 80%) |
|---|---|---|
| 0.95 | 0.0752 | 11.7% / **14.5%** |
| 0.97 | 0.0585 | 9.2% / **11.4%** |
| 0.99 | 0.0340 | 5.5% / **6.8%** |

**An ~11% volatility reduction is detectable at 80% power against the full multiple-testing
hurdle** — and that is squarely inside the range an inverse-vol construction plausibly
delivers. **The same panel that cannot see a 0.04 Sharpe gain can see a 10% vol cut with room
to spare**, because one statistic asks about means and the other does not.

`S13`'s own record is consistent with this and could not have shown it: alpha fell while
Sharpe rose, which is arithmetically possible **only if volatility fell**. The successor
register measures that fall directly, on the instrument that can see it. (I deliberately do
not back out the implied magnitude — that would be reconstructing an unpublished outcome
statistic.)

### **VERDICT 3 — THE FAMILY SURVIVES, RE-SPECIFIED: variance-primary with alpha
non-inferiority.** Full sketch: `PREREG_DRAFT_r1_variance_primary.md`.

---

## 4. THE CANDIDATE MAP — every candidate the commission named, with tags and verdicts

| candidate | graveyard tag | verdict |
|---|---|---|
| **Vol-weighted / risk-parity construction** | `S13` (rejected on an alpha gate its design could not move; Sharpe improved, drawdown flat) · `S5`/`S6`/`S24`/`S27` (the weighting family — but every corpse there re-weighted to chase RETURN; this targets variance and says so) | **ALIVE — R-1**, the family's flagship |
| **Factor-exposure neutralisation** (WRDS Beta Suite / Pastor–Stambaugh inputs) | `S15` + `SECTOR-NEUTRAL-B6` (neutralisation rejected twice, *"in every form is finished"*) · `X4` (factor-ETF benchmark, t 1.10) · `B21` (sector caps, unusually flat null) | **ALIVE, LOW PRIOR (~8%)** — it is a construction change and rides R-1's framework unchanged, but it inherits the neutralisation family's record and must argue past `S15` explicitly. Queue it *behind* R-1's verdict: if variance-primary cannot see a vol change from inverse-vol weighting, it will not see one from beta-neutralisation either |
| **Drawdown control** | `S10` (one market-wide quarter) · `S28` (20 of 69 quarters negative — the distribution is published) · `U3` (the overlay was leverage, not insurance) | **KILLED, n = 1.** Redirected to utility: `F-6`, `F-20`. A drawdown *disclosure* (the published quarterly distribution, already computed by `S28`) is `MB39`-class and free |
| **Crash-flag overlays on the equity book** | `MB8` (**KILL** — the 0.5× sizing haircut's reduction was NEGATIVE and *"the flag turns out nearly disjoint from the book it was meant to protect"*) · `E-4` (UNDERPOWERED: full sample clears all three legs at 3.19×, early half 1.69) · `E-5` (UNRESOLVED, hazard decays monotonically 9/9) | **KILLED for this book, and `MB8` is not arguable past:** you cannot lower a book's risk with a flag that does not fire on the book's names — that is arithmetic, not a prior. The flags remain alive **as separate books**, which is exactly where they already live (`O-1`, `F-9`, `F-11`). Anyone proposing an overlay must first move `MB8`'s disjointness measurement, not this file's opinion |
| **Turnover / cost-adjusted** | `S14` (**the record's ONE adoption** — a no-trade band adopted on NET alpha, i.e. a cost-inclusive gate) · `S14-WIDTH` (interior optimum confirmed) · `V5` (slippage) · `O18` (ρ = 0.6743) | **ALIVE, and it is not a risk gate — it is a COST gate, and it already won once.** Turnover is deterministic: no placebo floor exists or is needed. The honest extension is a **cost-model refinement** — better per-name impact estimates re-deriving `S14`'s band width — which is precisely what WRDS **Intraday Indicators** supplies (Part 1, W-16). Cheap, well-posed, and the only member of this family with a winning precedent |
| **Single-book Sharpe / risk DISCLOSURE** | `MB39` (the disclosure class) · `S28` (the distribution already ships) · `V3` (no per-name precision) | **ALIVE, zero trials.** Publish the book's Sharpe *with its honest CI* and the sentence this file exists to produce: *the interval is too wide for the number to decide anything.* That is a true, unusual, and publishable statement in `MB38`'s vocabulary |

---

## 5. WHAT THIS FILE DOES NOT LICENSE

It does not re-open `S13` on the alpha gate (that verdict stands on its own terms). It does not
license any weighting change to the shipped book — R-1 measures, it does not adopt. It does not
touch the long-short leg (`S13`'s row forbids reporting one from this construction class). It
does not make Sharpe a bar anywhere, including in the fleet: forward books would need roughly
4× their current fill horizons to resolve a Sharpe, which puts fleet Sharpe verdicts **5–10
years out** — stated so nobody quotes one at 30 fills. And it does not weaken the DSR, which
remains the project's only calibrated risk-adjusted bar and is `MB31`-stale at every new `N`.

---

# AMENDED 2026-08-25 — **DON'S RULING: R-1 IS PARKED, AND THE REASON IS ECONOMIC**
*(append-and-amend; nothing above is rewritten. The section above stands as written — this
records what it got wrong.)*

## 1. The ruling, and why it is right

**R-1's alpha non-inferiority margin is `X7`'s calibrated 1.8629pp — so the register could PASS
while surrendering 26.0% of the book's +7.17%/yr alpha (1.8629 ÷ 7.17). `S13` surrendered
1.76pp — 24.5% — and was REJECTED.** The register I designed could therefore have adopted a
larger alpha loss than the one the record already refused, and called it a pass. That is not a
subtle mis-calibration; it is a gate pointing the wrong way, and §3 above did not see it because
I priced the margin for **statistical resolvability** and never asked whether it was
**economically acceptable**. Those are different questions and I answered only one.

**Don's standing rule, recorded as binding on the whole family:**

> **A Sharpe or volatility gain bought with alpha is not worth having unless the Sharpe itself
> is bad — and it is not.** Book Sharpe **0.5866**, IR **≈0.88/yr against SPY**.

That is an economic precondition, and it belongs *before* the statistical design, not after it.
A risk register is worth writing only where the risk statistic is the binding complaint. Here it
is not: the book's problem has never been its Sharpe.

## 2. **STATUS: PARKED WITH A CONDITION** — not discarded, and the condition is checkable

R-1 re-opens only if **BOTH** hold:

* **(i) the margin is tightened to a level Don would adopt** — taken as **≈0.5pp/yr** (7.0% of
  the headline alpha) unless he names another; **and**
* **(ii) the design is still powered at that margin.**

## 3. The MB22 arithmetic for a ~0.5pp margin, both vocabularies

The paired alpha difference between two constructions on the same names, from published summary
statistics only (quarterly top-decile alpha **sd 3.298pp**, design effect **1.177** → `n_eff` =
69 × 0.850 = **58.65**), annualised:

`SE(Δalpha) = 4 × 3.298 × √(2(1−ρ)) ⁄ √58.65 = 1.7224 × √(2(1−ρ))` pp/yr

A margin `m` is **policeable** only if the design can distinguish Δ = 0 from Δ = −m: at 50%
power `m ≥ crit × SE`, at 80% power `m ≥ (crit + 0.84) × SE`, crit = **3.3133**.

| ρ (base vs arm returns) | SE (pp/yr) | smallest policeable margin — 50% / 80% power |
|---|---|---|
| 0.95 | 0.545 | 1.81 / 2.26 |
| 0.97 | 0.422 | **1.40 / 1.75** |
| 0.99 | 0.244 | 0.81 / 1.01 |
| 0.996 | 0.154 | **0.51** / 0.64 |
| 0.998 | 0.109 | 0.36 / **0.45** |
| 0.999 | 0.077 | 0.26 / 0.32 |

**Read three ways, and all three matter:**

1. **The margin I chose was the margin the design could see, not the margin Don would accept.**
   At a plausible ρ ≈ 0.97 the smallest policeable margin is **1.75pp at 80% power** — which is
   why 1.8629pp fit so neatly. The fit was a symptom, not a validation.
2. **A 0.5pp margin requires ρ ≥ 0.996 (50% power) or ρ ≥ 0.998 (80% power).** That is the
   condition, and it is a number someone can check.
3. **The gap is a factor of ~3.5** between what the design can police (≈1.75pp) and what is
   worth adopting (≈0.5pp), and only a very high arm-to-base correlation closes it.

**Unlike the Sharpe kill in §1, this is not self-defeating.** There, power required ρ → 1 and
ρ → 1 abolished the effect, because both lived in the first moment. Here the effect under test
lives in the **second** moment: two books can correlate at 0.998 in returns and still differ
in volatility (in the limit, `Y = 0.9X` correlates at 1.000 with 10% less vol). **So the
condition is satisfiable in principle** — it is an empirical question about how much composition
an inverse-vol re-weighting actually changes, and nobody has measured it.

## 4. How the condition gets tested — free, and before any register is rewritten

ρ is a correlation between two **return** series, so it is an outcome-touching measurement and
**this lane may not compute it**. It is cheap for the edge lane and needs no register:

**Build the arm's return series, compute ONLY ρ and the implied SE, bank them, and stop.** The
mean difference is *not* computed — the `MB15` separation exactly (marginal facts are
feasibility; their combination is the hypothesis), pinned the same way. Then:

* **ρ ≥ 0.998** → R-1 re-opens at a 0.5pp margin, and the rewrite is small: swap the margin,
  re-derive the power line, keep everything else in `PREREG_DRAFT_r1_variance_primary.md`.
* **ρ < 0.996** → R-1 **stays parked permanently on this panel**, and the parked reason upgrades
  from "Don declined the margin" to "no acceptable margin is policeable here" — which is a
  stronger and more durable closure than the one this file originally proposed.

**My honest expectation, written now: ρ lands in 0.95–0.99 and R-1 stays parked** (~70/30). An
inverse-vol re-weighting changes position sizes across ~250 names; that is more composition
change than ρ ≥ 0.998 allows.

## 5. What this ruling does to the rest of the family

The economic precondition binds **every** entry in §4's candidate table, and two change status:

* **Factor-exposure neutralisation** — was ALIVE/LOW-PRIOR; now **PARKED under the same rule**.
  It is a construction change with the same shape and the same problem: whatever variance it
  buys, it buys with alpha, and the Sharpe it would improve is not the binding complaint.
  Re-opens on the same two-part condition.
* **Turnover / cost-adjusted** — **UNAFFECTED, and now the family's only live member.** It is
  the one variant that does not trade alpha for risk: it *keeps* alpha by spending less. `S14`
  is the record's single adoption and it won exactly there. Don's rule does not touch it —
  which is itself an argument that the cost axis, not the risk axis, is where this project's
  remaining edge lives.
* The single-book Sharpe **disclosure** is likewise unaffected (it decides nothing) and is now
  the honest public form of this whole investigation: *we looked, and the number cannot decide.*
