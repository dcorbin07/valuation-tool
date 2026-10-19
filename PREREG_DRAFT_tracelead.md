# PREREG_DRAFT_tracelead.md — do corporate-bond spread changes lead the stock? — 2026-10-18

**A DRAFT, NOT A REGISTER. ZERO TRIALS.** No arm has run, no coverage of the *signal* measured, no
forward return read. **r1 executes; the Frontier Scout drafts.** A register exists only once this
file is committed **ALONE**, markdown only, zero `.py`, as a strict git ancestor of every
measurement commit, with its trials booked **before** any runner exists.

**Ranked #1 in `EDGE_DATA_MAP.md`**, on a single measured fact: it is the only candidate this
project has ever scoped whose data coverage **improves** as the company gets bigger.

---

## 1. THE HYPOTHESIS, AND WHAT MAKES IT DIFFERENT FROM EVERY RECENT NULL

**A company's own credit market reprices its risk continuously, and the equity market may be slower
to read it.** So: *does the change in a firm's corporate-bond credit spread over the quarter predict
its equity return over the next quarter, incrementally to the deployed composite?*

**WHY THIS IS NOT ANOTHER ORTHOGONALITY ITEM, which is the argument that has to be made first.** The
record's most repeated pattern is eight items — `U2`, `MA31`/`MA32`, `MA58`, `MB18`, `D6`, `E-2`,
`E-3`, `E-6` — **confirmed orthogonal at R² 0.027–0.145 and not one clearing**, and
`IDEAS_LEDGER.md` records *"orthogonality anything"* as a **standing design-level kill.**

> **THE DISTINCTION IS THE SOURCE, NOT THE STATISTIC.** Every one of those eight is a **different
> function of data the composite already reads** — the same filings, the same prices, the same
> chains, re-arranged. **A bond spread is a price set by a different set of participants in a
> different market.** That is not an orthogonality argument (which this record has killed) but a
> **new-information** argument, and it is the only candidate on the board that can make it.
>
> **AND IT IS STILL NOT SUFFICIENT.** `U2` measured options-surface levels — also a different
> market, also different participants — at R² 0.055–0.088 against the incumbents, i.e. **genuinely
> new information that predicted nothing.** So this draft's prior must be set **below** a coin flip,
> and §8 does that.

---

## 2. THE OBJECT, DEFINED SO IT CANNOT DRIFT

For each (date *t*, name *i*) in the **$10B tier** of the corrected raw universe:

1. Take every bond of issuer *i* trading in the 63 sessions before *t*, from `trace.trace_enhanced`.
2. **Spread** = the trade yield minus the maturity-matched Treasury yield, **per bond, per day**,
   volume-weighted within the day.
3. **`bond_spread_chg`** = the change in the issuer's **duration-weighted mean spread** from
   (*t* − 126 sessions) to *t*, in basis points.
4. **Declared sign: NEGATIVE.** A *widening* spread predicts a *lower* equity return. Fixed here,
   before any measurement, and a positive result is **not** a pass.

**THREE CONSTRUCTION DECISIONS FIXED NOW, each because the obvious alternative is a known trap:**

- **DURATION-WEIGHTED, NOT EQUAL-WEIGHTED, across an issuer's bonds.** A median covered issuer has
  **six to nine** traded bonds of different maturities, and an equal-weighted mean would let one
  thinly-traded 30-year bond dominate a 2-year curve.
- **THE CHANGE, NOT THE LEVEL.** The *level* of a credit spread is close to a rating, and a rating
  is close to `quality` plus `size` — which is `R6`'s and `E-1`'s death (a conviction aggregate that
  decomposed into a size sort at −0.815 to −0.854 and 0.6114 respectively). **The change is the
  object; the level is a control.**
- **NO WINSORISATION BEYOND `zscore`'s SHIPPED 2% CLIP.** `S21` measured that removing it moves
  top-decile alpha by +2.43pp and that the unclipped arm's extreme name averages **7.14× its own
  99th percentile** — so the clip is load-bearing and is not a free parameter.

---

## 3. THE FREE PRE-OUTCOME KILLS — all four run and are READ before any arm, in their own pass

**`O10`'s process defect is not repeated: the kills run in a separate invocation and the arm runner
REFUSES without a passing kill artifact.** Under `MB1-SEL` a control can only ever BLOCK, so **the
kills cost ZERO trials** and may be run before any register is committed.

| kill | what it measures | bar | why this bar |
|---|---|---|---|
| **`K1` COVERAGE** | share of $10B-tier cells with ≥ 1 bond trading in the 63-session window, **per date**, and the per-date minimum | **≥ 0.70 of cells AND no date below 0.50** | `W-28` set a 90% bar on a Compustat linkage, watched 57 of 69 dates fail it, and established that **a successor may not relax a pre-committed bar after watching it fail.** So this bar is set on the **measured** 81–98% issuer coverage with headroom for the bond-level requirement being stricter than the issuer-level one, and **not at 90%** |
| **`K2` COSTUME vs `low_risk`** | mean per-date \|Spearman\| of `bond_spread_chg` against the `low_risk` theme | **< 0.60 or the arm is WITHDRAWN** | `E-1` was withdrawn at 0.6114 against `size`; a credit spread and an equity-volatility measure are the same latent risk read two ways |
| **`K3` COSTUME vs `quality`** | the same against `quality`, **and against `size`** | **< 0.60 each** | the level-vs-change decision above is an argument; this is the measurement that checks it |
| **`K4` REPRODUCTION** | the composite the arm residualises against reproduces the landed record elementwise | **max \|Δ\| = 0.000e+00, on a GATED non-zero cell count** | `MB21`'s `C1` scored a perfect zero on an **empty** frame by comparing nothing; `W-1`'s `K4` fired twice against correct panels |

**`K1` IS THE ONE MOST LIKELY TO FIRE AND THAT IS PRICED IN §8.** The 81–98% figure is **issuers
with any trade in a quarter**; requiring a **maturity-matched spread at two dates 126 sessions
apart** is strictly harder, and nobody has measured how much harder.

---

## 4. THE ARM — ONE ARM, NO GRID

**Charter §1a, exactly:** incremental information against **the deployed composite as a single
control**, never against the seven themes separately.

> **AND THAT IS NOT A STYLISTIC CHOICE: `STAGE1-BATCH1` records complete-case residualisation on the
> seven incumbents leaving 25 of 44 build-quadrant dates with a FIVE-DATE early half against a
> 16-date floor, so its three scored arms came back BOTH-HALVES NOT ASSESSABLE.** A seven-theme
> residualisation here would produce an unreadable arm.

- **Build quadrant only:** 2009-2019 × `sha1(ticker) % 2 == 0`, ~44 dates.
- **Statistic:** the per-date Spearman IC of `bond_spread_chg` residualised on the composite against
  the forward 63-day return, with a Newey-West *t* at lag 1 (**`R9` measured lag-1 +0.189 on this
  project's own spread**, so the naive *t* is a diagnostic only).
- **Both halves of the build quadrant, agreeing in sign**, which is the rule that has killed more
  items in this record than any bar.
- **Scored on BOTH populations with the $10B tier GOVERNING** (charter §1b). `STAGE1-BATCH3` had
  three arms real on the wide universe and absent in the tier — *"REAL BUT NOT INVESTABLE HERE"* —
  and that label must stay reachable.

**THE BAR IS DERIVED AT THE REGISTER'S OWN `N`, NEVER QUOTED.** `UNIVERSE-BIAS-2` moved the headline
to HAC *t* **1.0780** and `STAGE1-BATCH1` states that **no bar measured on the 2,531-name panel
transfers and no X7 floor may be quoted.** So the register derives `sqrt(2 ln N)` at its own booked
`N` and **labels every critical value UNCALIBRATED** (`V2G`, `R1-VAR`: no calibrated floor exists for
a statistic this panel has not had a placebo sweep for).

**AND THE MDE TRAVELS WITH THE VERDICT (`MB22`, and the 80%-power form `(crit + 0.84)·se`).** On ~44
dates the 80%-power MDE is **≈ 0.637 SD**, against **the strongest raw anchor this panel has ever
carried at 0.4346 SD** (`MB18`'s `z_fcf_margin`). **So a null here means "nothing larger than the
largest thing we have ever held", and the register says so in advance rather than discovering it.**

---

## 5. TRIALS, AND THE DOMAIN

**1 equity trial**, booked **before any runner exists**, charged to **equity** (the signal predicts
the underlying's return, `U2`'s precedent). The four kills charge **zero** under `MB1-SEL`.

**Equity `N` 307 → 308**, hurdle **derived** at the booking commit and never typed from this file —
`MB32`'s rule, after an options hurdle moved *while that item was being written*.

---

## 6. VOID CONDITIONS

1. **Quoting a bar or floor measured on the 2,531-name panel.**
2. **Running a second construction** (level instead of change, a different window, equal-weighting,
   a different spread definition) **in this register.** Each is a new hypothesis with its own trial.
   This is `V6`'s and `MB1`'s void condition and it is what stops a grid wearing one arm's clothes.
3. **Relaxing `K1` after reading it.** `W-28`'s §6 rule.
4. **Reading the check quadrant.** Charter §2 permits ONE read and it is not this register's.
5. **Quoting any figure from the FINRA free feed as the researched signal**, or vice versa — they
   are different objects (§7).
6. **Quoting the 81–98% issuer coverage as the arm's coverage.** It is `K1`'s input, not its output,
   and `O-1` lost ~17× of power by applying a coverage figure measured on one population to another.

---

## 7. THE LIVE ROUTE, AND THE ONE THING THAT MUST BE VERIFIED BEFORE ADOPTION IS EVEN DISCUSSED

**The research rung reads the entitled WRDS `trace.trace_enhanced`. That copy may NEVER feed the
live score** — WRDS is academic-research-only and this repo is public.

**The live rung reads FINRA's own free TRACE dissemination.** **TWO LIMITS, BOTH STATED AS FACTS TO
CHECK RATHER THAN ASSUMPTIONS:**

1. the public feed is **delayed and aggregated** relative to the academic file;
2. **dissemination caps on large trades** differ between them.

**So the live signal will not be bit-identical to the researched one**, and `COVERAGE-IS-NOT-FIDELITY`
is the governing lesson: a live column can pass every coverage bound and still not be the thing it
is named after. **An adoption would require its own fidelity gate comparing the FINRA-rebuilt signal
against the WRDS-built one on an overlap** — and that gate is **not** in this register.

---

## 8. EXPECTATIONS, STATED IN ADVANCE AND PRICED

| # | expectation | odds |
|---|---|---|
| 1 | **`K1` does NOT fire** (≥ 0.70 of tier cells carry a two-date maturity-matched spread) | **55/45** |
| 2 | `K2` and `K3` both pass (no costume) | 75/25 |
| 3 | **the arm is NULL** | **70/30** |
| 4 | if the arm resolves at all, the sign is as declared (negative) | 70/30 |
| 5 | the wide universe reads stronger than the $10B tier | 65/35 |
| 6 | **the $10B tier alone clears** | **20/80** |

**EXPECTATION 3 IS THE HONEST HEADLINE AND IT IS NOT PESSIMISM, IT IS THE RECORD.** `0-for-23` on
literature candidates through this exact design; the one equity signal that clears
(`INSIDER-WIDE`, +3.4888pp on cap > $500M) **reads *t* 0.732 in the $10B tier**; and `U2` showed a
different market's prices can be new information and still predict nothing.

**WHAT MAKES IT WORTH ONE TRIAL ANYWAY: the coverage.** Every other new-data candidate this project
has scoped was killed or crippled by thin data in large names — `institutional` empty before
2013-06-30, the options cache at ~40% of the tier, `O-1`'s freeze at 5.89% of cells, `W-28`'s dated
linkage unreachable at 90%. **This is the first candidate where the $10B tier is the *best*-covered
part of the data rather than the worst**, so a null here would be a null **about the hypothesis**
rather than about coverage — which is the one thing the last three Stage-1 batches could rarely say.

---

## 9. WHAT THIS DRAFT DOES NOT CLAIM

It does **not** claim bond spreads predict equity returns — **no arm has run.** It does **not**
reopen `W-19`, whose crash-flag version is a different hypothesis and keeps its own verdict. It does
**not** claim the FINRA feed is adequate; §7 names two limits as facts to verify. It does **not**
propose adopting anything. And **its literature leg is INCOMPLETE and declared so**: the bond
lead-lag papers (Kwan 1996, JFE, and a 2026 replication) were **identified by name and not read**,
because the surveying agent died on a session limit mid-fetch. **The register's first non-data act is
to read them** — and if they point the other way, that is a finding available **before** a trial is
spent, which is the cheapest possible outcome.
