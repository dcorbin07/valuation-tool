# PREREG — O-1: long puts on accounting-flagged names

**Status: BLIND. Committed ALONE, markdown only, zero `.py`, as a strict git ancestor of every
measurement commit.** No runner exists. Nothing below has been computed on any return. The power
arithmetic in §6 is pure arithmetic on the hurdle and was computed before any floor was written —
which is `EVOWN`'s self-reported defect, not repeated.

**THE ENTIRE O-SERIES BOOK IS 100% CALLS.** `O13` measured `opt_right` **constant** across all
3,870 banked trades, so *every* options claim this project has made is about long calls at swing
horizon. **Long puts have never been tested.** That is the gap this item opens, and it is a NEW
BOOK — see §8.

---

## 1. THE MECHANISM

`MA28-CARD` is the strongest replicated risk result the project owns. Names tripping **2 or more**
of Beneish M > −1.78, Altman Z < 1.81, and top-decile within-date external financing lost **more
than half their value over the next 63 trading days**:

| | flagged | kept | ratio |
|---|---|---|---|
| full | **2.6597%** | **0.8743%** | **3.0422** |
| early | — | — | 3.4209 |
| late | — | — | 2.9321 |

* **Every window's observed value exceeds the permutation MAXIMUM of 500 draws**, not merely the
  p95 (empirical *p* < 0.002 each).
* **It survives the size control that killed three sibling items** (`U7`, `S10`, `V6-B`): 5 of 5
  market-cap quintiles clear, and it is **STRONGEST in megacaps** (2.010× smallest → **5.169×**
  megacap) — the opposite shape from a size sort.
* The thresholds are **Beneish's and Altman's published values**; this panel fitted none of them.
* `E-5` independently reproduced the instrument on five counts, including the full-sample ratio to
  sixteen digits (3.0422123745999063) and 6,542 flagged rows at a 5.7414% flagged share.

**A put is the instrument that pays on exactly that event.** The card predicts a crash; nothing has
ever asked whether the crash is purchasable.

---

## 2. THE PRE-OUTCOME KILL — ITS OWN PASS, READ BEFORE ANY ARM

**Does the market already price the flag?** If flagged names' options already carry a fatter left
tail, the put is already expensive and the edge is dead before an arm runs. **That is a finding,
not a failed session**, and it saves the trial.

**Instrument: `I-1`'s shipped `valuation/studies/rnd.py`, IMPORTED** — Breeden–Litzenberger
risk-neutral densities from the **frozen** chains, whose `K1` put–call-parity control clears at
**0.9858** against a 0.95 bar. A second density implementation would be the `B7` defect class.

**Statistic:** risk-neutral left-tail mass `Q(S_T < x·S_0)` per name-day, flagged vs unflagged, at
**pre-declared thresholds x ∈ {0.50, 0.65, 0.80}**. **0.50 is the primary** because it is
`MA28`'s own crash definition; 0.65 and 0.80 are declared secondaries carrying no kill power.

**KILL CONDITION, fixed now:** the arm is **WITHDRAWN before any outcome is read** if the
flagged/unflagged left-tail-mass ratio at x = 0.50 is **≥ 2.0** in the full sample. **2.0 is
`MA28`'s own ratio bar, reused verbatim** rather than chosen here — the same bar the flag itself
was judged on. At ≥ 2.0 the market has already priced most of the 3.0422× crash-rate ratio.

**`scripts/o1_arm.py` REFUSES to run without a passing kill artifact**, and that refusal is
**mutation-tested** — a gate that cannot bite is not a gate (`DEEPITM-FIN`'s standard).

**THE RELATIONSHIP TO `E-4`, DECLARED RATHER THAN DISCOVERED — and it is the single most important
paragraph in this register.** `E-4` built the option-implied left-tail flag on this same card and
measured the two flags to be **very nearly INDEPENDENT: Cohen's kappa 0.0624, odds ratio 2.4257.**
The market flag fires on 20.04% of rows and carries 24 of 54 crashes; the accounting flag on 4.22%
carrying 9; their union 22.71% carrying 28; **neither flag sees the other 26.**

* **So `E-4` is strong prior evidence that this kill will NOT fire**, and I say so in advance
  rather than presenting a pass as a discovery.
* **It is nevertheless a different question, and the difference is not a technicality.** `E-4`
  measured co-occurrence of two **BINARY** flags. This kill measures whether the **CONTINUOUS**
  left-tail mass is systematically higher on flagged names. Two binaries can be near-independent
  while the underlying continuous quantity still differs on average — kappa is insensitive to a
  shift that never crosses the threshold.
* **`E-4`'s verdict is UNDERPOWERED and is NOT reopened.** Nothing here re-scores its arm, and its
  ratio of 3.1914 is quoted only as context.

---

## 3. GRAVEYARD TAGS — argued past in writing, or the item dies here

**A3 / O9 — short vol.** `A3` rejected selling volatility at **−7.99%/trade**. **This is the
OPPOSITE SIDE of the trade.** A closed short-vol family says the premium is *not* collectable at
these strikes and tenors; it says nothing about whether it is *payable*. **The two claims are not
negations of each other** — a market can be one where selling vol loses money *and* buying it
loses money, which is the usual case once spread is paid, and that is precisely what this item is
built to find out rather than assume. **It is not a costume**: no arm here sells anything, and the
verdict cannot be reached by re-signing `A3`'s.

**U3 — the convex overlay.** `U3` found the sleeve was **leverage, not insurance** — correlation
**+0.4371** to the equity book, **−84.39%** in its worst four quarters. **But that sleeve was
INDEX-LEVEL exposure applied to the WHOLE BOOK**, and its own measurement was that it was `call`
on **3,870 of 3,870** rows at mean delta **+0.3725** — long delta *and* long vega. **This is
single-name PUTS on a flagged subset**: short delta by construction, and targeted at names with a
measured 3.04× crash rate rather than at the market. `U3`'s finding is that a long-vol overlay
bought indiscriminately is leverage; it is silent on one bought selectively.

**V6-OPT — and this contrast is the item's whole licence, so it is stated precisely.** `V6-OPT`
**SOLD** cash-secured puts on "healthy" dips and was rejected on **condition 2**: the identical
trade on **UNHEALTHY** dips earned **MORE** (+1.2651% vs +1.1342%), in **both halves**. **The
health floors did not discriminate.** The reason was measured: a **delta-targeted** rule sets the
strike from the name's own volatility, so it neutralises the very risk difference the trade was
built to exploit — assignment came back **25.30% vs 25.73%**, a 0.43pp gap. **`MA28`'s flags DO
discriminate, on the same axis and on the same panel:** 2.6597% vs 0.8743%, a **3.04×** ratio, in
both halves, against the permutation maximum, and strongest in megacaps. **So the precise contrast
is: `V6-OPT` failed because its conditioning variable carried no crash information; this item's
conditioning variable carries the largest replicated crash separation in the record.** That is the
licence, and if the kill in §2 shows the market has already priced it, the licence is void.

**E-4 — see §2.** Declared, not discovered.

**MB8 — and this is the one most likely to be misread.** `MB8` killed the flag as a **sizing
haircut** and found it **nearly DISJOINT from the top-decile BOOK**: **407 flagged holdings of
11,426 = 3.56%**, carrying **one crash of eighty-four (1.19%)**, with **ZERO flagged crashes in
the whole early half**. **O-1 IS ON THE PANEL, NOT ON THE BOOK.** The panel-wide flagged share is
**5.74%** carrying **19.14%** of crash exposure — an order of magnitude more than the book's 1.19%
— because *the composite already declines to hold what the flag catches*. **A put book does not
need the composite to hold the name.** Nobody may read a result here as a statement about the
top-decile book, and a test pins that no arm path reads a book file.

---

## 4. TENOR IS PRE-DECLARED, AND `E-5` BINDS

`E-5` measured the hazard curve of a flagged name and returned **UNRESOLVED** — but its two
component measurements are what fix tenor here:

* the excess crash **HAZARD** decays **monotonically, 9 of 9 steps down**, clearing its null's
  **maximum**;
* the excess crash **COUNT** peaks in the **SECOND quarter**, and its 60% excess-share bar failed
  at **0.5701** — so **quarters three and four together carry ~42.99% of the four-quarter excess.**

> **"The flags decay, therefore buy short-dated" is the one inference `E-5` refutes.** A hazard
> that falls while the count peaks later means the *rate* is highest early and the *mass* is not.
> A 45–75 DTE put — the engine's own band, and every tenor this project has ever traded — spans
> roughly the FIRST quarter only and would miss the peak of the excess it is buying.

**PRIMARY TENOR: 150–210 DTE**, which spans the first two quarters and therefore the Q2 peak, and
captures the **57.01%** of four-quarter excess that `E-5` places in Q1+Q2. **DECLARED SECONDARY,
no verdict power: 330–400 DTE**, which reaches the remaining ~43%.

**The engine's 45–75 DTE band is NOT run and carries no verdict here** — declaring it would be
buying the tenor `E-5` refutes. **Tier C/E strata are quotable since `S3-I5`** (36 REUSED, 7
SPLIT_YEAR, 2 SAME_COMPANY; cross-table control 25/26), which is what makes 150–400 DTE reachable
at all.

---

## 5. THE ARM

* **Universe:** the panel's flagged rows, on names with a usable chain at the declared tenor.
  Flagged = `MA28`'s 2-of-3, **imported**, never re-implemented.
* **Control:** unflagged panel rows **matched on name-year and market-cap quintile**, matched by
  design rather than checked afterwards (`EVOWN`'s lesson). An unmatched cell is **dropped and
  counted**, never matched loosely.
* **Instrument:** long put, strike by the engine's own moneyness band, entry and exit through the
  **shipped** fill and exit machinery, imported.
* **Statistic: the MEAN return gap.** **The median is BANNED by measurement** — `O17C4` recorded
  the effect as *"a MEAN effect, not a MEDIAN one"*, `MB1` reproduced it, `MB1-SEL` pinned the ban
  by AST, and `EVOWN` inherited it. Pinned by AST here, scoped to **returns** (a tenor's median is
  an ordinary descriptive).
* **Uncertainty:** paired **name-year cluster bootstrap**, `R3`'s own unit (design effect 2.1837
  against a shuffled-null p95 of 1.1898), 2,000 draws, seed 20260824.
* **Costs at the measured toll:** `O18`'s **ρ = 0.6743**. **THIS IS AN EXTRAPOLATION AND IS
  LABELLED ONE EVERYWHERE IT APPEARS** — ρ was measured on **35-delta ~60-DTE CALLS**, and this
  book is **PUTS at 150–400 DTE**. Both the ρ-adjusted and the full-quoted-spread figures ship,
  and the verdict is taken on the **full quoted spread**, which is the conservative side.

---

## 6. POWER BEFORE FLOORS — the arithmetic, on the page, before any floor is written

At the options hurdle for `N` = 308 (**3.3853**):

* **50%-power multiplier (`crit·se`): 3.3853** — this is what every MDE this project has published
  actually is.
* **80%-power multiplier (`(crit + 0.84)·se`): 4.2253**, larger by **1.2481×**.

| effect (SD units) | independent trades required at 80% power |
|---|---|
| 0.050 | **7,141** |
| 0.075 | **3,174** |
| 0.100 | **1,785** |
| 0.150 | 793 |
| 0.200 | 446 |

| n | MDE at 80% power |
|---|---|
| 500 | 0.1890 SD |
| 1,000 | 0.1336 SD |
| 2,000 | 0.0945 SD |
| 4,000 | 0.0668 SD |

**THE FLOOR IS DERIVED FROM POWER, NOT FROM `n`.** A rough prior on the effect: a 1.79pp higher
crash rate, on an instrument where a crash is worth of order +300% against a base near −50%,
implies a mean gap of order **+6pp** on a return distribution whose SD on this project's option
books runs near **90pp** — about **0.07 SD**, which needs roughly **3,600 matched trades**.

**So the floor is 3,600 matched flagged trades, with at least 1,200 in each half.** Below it the
verdict is **UNDERPOWERED, never null**, and that is knowable **in advance**: the panel carries
**6,542** flagged rows, so at the ~75% chain coverage this project measures elsewhere the design
sits close to its own floor rather than comfortably above it. **If it lands below, the honest
outcome is UNDERPOWERED and the trial still charges.**

**The MDE ships with the verdict at BOTH vocabularies or the verdict is not reported.**

---

## 7. Void conditions

1. The median computed on a return anywhere in the arm path.
2. The arm run without a passing kill artifact.
3. The 45–75 DTE band reported as an arm, or the secondary tenor reported as the primary.
4. Any book file read in the arm path — **this is the PANEL, not the book** (`MB8`).
5. `E-4` or `A3`/`O9` re-scored, or their verdicts moved.
6. ρ = 0.6743 quoted without its extrapolation label.
7. A verdict reported without its MDE at both vocabularies.
8. Any result read as rescuing the alert book. **`R2` stands at −5.0640pp/trade against random
   entry.** `O11` governs and nothing here licenses a trade.

---

## 8. Scope

**A NEW BOOK.** Not the alert book, not the top-decile book. Read from the **pinned freezes only**,
via the shared resolver, which **raises** rather than falling back. `pre_panel_history` filtered.
Strikes and settlement on **as-traded** prices (`U1-SPLIT`). **ADOPTS NOTHING.**

---

## 9. Prior

| outcome | prior |
|---|---|
| the KILL fires (market already prices it) | **15%** — `E-4`'s kappa 0.0624 argues against it |
| arm runs and is **UNDERPOWERED** | **35%** |
| arm runs and is **NULL** | **35%** |
| arm runs and **separates** | **15%** |

**I expect the kill NOT to fire and the arm to struggle on power rather than on sign**, because the
floor in §6 sits close to what the panel can supply. **The most likely single outcome is that this
returns a bounded null or an underpowered verdict** — and per §6 that is stated with its MDE or not
at all.

Secondary expectations: **E1** the left-tail ratio at x = 0.50 lands between 1.0 and 2.0 (70%);
**E2** matched trades land below 4,000 (65%); **E3** the 150–210 DTE gap exceeds the 45–75 DTE gap
this register does not run (55%, unscorable by design and recorded only to be honest that I hold
it).
