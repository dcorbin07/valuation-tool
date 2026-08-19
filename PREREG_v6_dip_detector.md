# PRE-REGISTRATION — V6: the Dip Detector's testable claim

**Registered 2026-08-13, blind, BEFORE the tab exists and before any of its copy is written.**
This file is committed **ALONE** — one `.md`, zero `.py` — and is a strict git ancestor of every
commit that measures anything. Nothing in it was chosen after seeing a forward return.

**The claim under test, in Don's words:** *a QUALITY-CONDITIONED drawdown recovers better than the
market.*

---

## 0. Why the ordering here is unusually clean, and what that does and does not buy

The Dip Detector tab **does not exist**. Measured, not assumed: the string `dip` (case-insensitive,
word-boundary) appears nowhere in `valuation/`, in any template, or in any `.md` spec in this
repository except in unrelated options-lane prose about option prices dipping through a stop. There
is no `V6` row in `VALQUO_EXTENSIONS.md` (which runs V1–V5) and no `V6` row in `VALQUO_LEDGER.md`.

So this register is written **before the product copy it will govern**, not merely before the
measurement. That is the strongest ordering available and it is worth stating plainly, because the
usual failure mode of a "we tested our feature" claim is that the feature's language was written
first and the test was shaped to clear it.

**What it does not buy:** registering early does not make the test powerful, and it does not make
the panel able to answer a question about the live product. §2 is the limit, and it is committed
here rather than discovered later.

---

## 1. Premise findings — measured BEFORE this register was written, none of them a forward return

Every number in this section is a fact about what data exists or how often a condition occurs. **No
forward return was computed, at any horizon, before this file was committed.** Precedent: S17/S19
measured premises first and said so.

### 1a. The prior the task states is real but weaker than it sounds, and it is also a DIFFERENT OBJECT

The task states the prior honestly: *plain short-term reversal FAILED to replicate on this panel
pre-audit.* That is true as written — `RESEARCH_LOG.md:140` records
`P4-3 | 2026-07-29 | equity | Classic anomalies replicate on this panel | signal IC t | REJECTED |
n=4` covering reversal, idio-vol, MAX and low-vol.

**Two things weaken it, and both are in this project's own record.**

1. **That rejection ran on an ALPHABETICAL slice.** Audit **B12** established that
   `WRDSProvider.universe` returned `sorted(keys)[:limit]`, so the entire 800-name era was names
   beginning with roughly **A through C** — not the 800 largest. `CLAUDE.md` names these exact four
   classic-anomaly rejections in its list of results that **need a full-universe re-run before they
   are cited again**. So short-term reversal is not cleanly rejected on this panel; it is
   **untested on the corrected universe**.
2. **A drawdown is not a reversal.** Short-term reversal sorts on a **1-month return change**. This
   register sorts on a **level** — how far a name sits below a 252-day trailing high. A name can be
   20% below its high while its last month was strongly positive, and vice versa. They are
   different features and the correlation between them is not assumed here; **C7 measures it.**

**Consequence, committed now:** the prior is directionally discouraging and is **not** a
near-replication. A null here may **not** be reported as "reversal failed again", and a positive
here may **not** be reported as overturning P4-3. Neither statement would be about the same object.

### 1b. The financial-health leg is BUILDABLE with no panel rebuild — the exact opposite of S10

S10's accounting half was excluded from the S17/S19 register because eight SF1 columns were absent
from `WRDSProvider._KEEP`, forcing a rebuild. **That is not the situation here.** Every input the
shipped health sub-score needs is already in `_KEEP` **and** populated in the export
(197,265 ARQ rows):

| column | coverage | used for |
|---|---|---|
| `debt` | 0.9996 | net debt |
| `cashneq` | 0.9996 | net debt |
| `ebitda` | 0.9569 | net debt / EBITDA |
| `intexp` | 0.9769 | interest coverage |
| `ebit` | 0.9768 | interest coverage, margin |
| `fcf` | 0.9647 | positive-FCF term |
| `currentratio` | 0.8158 | not used (recorded for completeness) |

Derived and computable: **net debt / EBITDA on 83.38%** of rows, **interest coverage on 75.34%**,
**at least one of the two on 92.64%**, FCF sign known on 96.47%. Medians: net debt/EBITDA 5.7869,
interest coverage 5.0338.

**So V6 charges no rebuild and no new data.** This is stated because the S17/S19 register had to
decline S10 for precisely the opposite reason, and the difference is a fact about the export rather
than a preference.

### 1c. `roic` and `roe` are 0.0% populated and must be DERIVED, never read

Coverage of `roic` and `roe` in the ARQ export is **0.0000** — exactly as `CLAUDE.md` and the
`_KEEP` comment record (Sharadar fills them only for ART/ARY). The quality leg therefore **derives**
its inputs from line items and **never reads those two columns**. A construction that read them
would compute cleanly on an all-NaN column and silently condition on nothing. **C4 pins this.**

### 1d. A dead fallback found in passing — reported, not repaired

`_KEEP["fundamentals"]` requests **`ebitmargin`**, and the export **does not contain that column**
(it ships `ebitdamargin` and `netmargin`). So the fallback at `fundamental_panel.py:405` —
`_f(sf1, "ebitmargin")`, reached only when `ebit` or `revenue` is missing — is **unreachable**.

This changes nothing: the primary `ebit / revenue` path works and this register derives margins from
line items regardless. It is recorded because it is the **COVERAGE RULE class in a new costume** —
*a name in an allowlist is not evidence the column exists* — and because the neighbouring
`grossmargin` fallback on the next line **is** live, so the two lines look identical and are not.
**Not repaired: it is on the shipped panel's path, it moves no number, and repairing it inside a
register would make this lane's panel stop being the shipped panel.**

### 1e. The design is FEASIBLE at both depths — and the flag is violently time-varying

Measured over 111 probe dates spanning 1998-12-31 → 2026-07-23 on an 860-name usable price sample
(2,998 price files exist; the panel's cross-sections run larger, so these counts are conservative):

| depth | median share of names flagged | min | max | median count |
|---|---|---|---|---|
| ≥ 20% below trailing high | **25.45%** | 4.35% | 82.32% | 170 |
| ≥ 30% below trailing high | **14.92%** | 1.89% | 69.15% | 96 |

**Zero of 111 probe dates carry fewer than 10 names at the 30% depth.** So neither arm faces S18's
or U2's impossibility — a full both-halves gate on the whole panel is available at both depths, and
this register does **not** need to substitute a covered-subsample gate.

**The structural fact that decides which leg is informative:** the share flagged ranges from
**4.35% to 82.32%**. At a date where 82% of the universe is 20% below its high, "is this name
dipped" carries almost no cross-sectional information — the flagged set *is* roughly the universe —
and any comparison against the universe on such a date measures little. The two legs in §3 are not
redundant, and §3.5 commits which one carries the claim.

### 1f. The tab's own sub-scores are NOT computable point-in-time — this is the binding limit

The tab would read `valuation/engine/scoring.py`'s `quality` and `health` sub-scores. Those take a
`CompanyData` and a `Classification` and are computed on the **live** data path. They cannot be
reproduced point-in-time across 2,531 names × 69 dates:

* `_quality_score(cd, wacc)` needs a **WACC**, which needs a beta. **S23 measured that the
  point-in-time valuation path was fetching LIVE Yahoo prices** through `_resolve_beta` — valuing
  1999 with a beta regressed on 2021–2026 returns — and that lane had to add an explicit offline
  mode. A per-date WACC for the whole panel is a build with its own register, not a control here.
* The full engine (classification, Monte Carlo, comps) is not runnable per name per date at this
  scale, and S23's own experience is that attempting it silently reaches the network.

**So the arm cannot use the tab's sub-scores.** What it uses instead is committed in §3.2, and the
consequence is committed in §2.

---

## 2. THE CONSTRUCT DIVERGENCE, AND THE ASYMMETRY IT FORCES — committed before any result

The arm conditions on **the panel's own `quality` theme** and on **a point-in-time health score
built from the SHIPPED `_lerp` breakpoints in `scoring.py`, imported rather than restated**. That is
the closest object the panel can express. It is **not** the tab's live sub-score pair.

This is the U2 near-miss in a new costume: *a lookup by column name computes cleanly, raises
nothing, and reports a verdict on a construction the product never uses.* Naming it in advance is
the only thing that stops it happening.

**The asymmetry, fixed here in writing, because it is what makes the result usable either way:**

* **A NULL or a REJECT here IS informative about the tab's claim.** The panel's `quality` theme is
  the **strongest theme in the panel** (IC *t* **+3.10**, one of only two clearing X7's calibrated
  2.71 bar). If conditioning a dip on the panel's best available quality measure plus a health floor
  built from the product's own breakpoints does not rescue it, the claim that *some* quality
  conditioning rescues a dip is in serious trouble — I used the most favourable instrument available.
* **A POSITIVE here does NOT license the tab's copy.** It would establish the effect for the
  **panel's** construction only. Shipping a number would additionally require a live-vs-panel
  **fidelity** check — the `coverage-is-not-fidelity` lesson, where a live column passed every
  coverage bound and still was not the theme it was named after. **That check is explicitly NOT part
  of this register and a positive verdict must say so.**

---

## 3. Design

### 3.1 One panel, one build

`build_fundamental_panel(..., lookback_years=CONFIG.backtest_lookback_years, horizon=63,
extra_horizons=(126,))` on the **full universe** (~2,531 names, 69 dates). S22's `extra_horizons`
computes `fwd_ret_h126` **inside the same loop from the same price array** as the shipped
`fwd_ret`, so the two horizons share dates, names, scores and cross-sections exactly and **no
difference between them can be an artefact of the date set**. A build per horizon is forbidden here
for that reason.

A run whose panel is not the canonical shape (`lookback_years` default 6 gives a 21-date smoke test)
**asserts and aborts**, per the METHODOLOGY RULE and S3's own defect.

### 3.2 The drawdown feature — and the split trap, named in advance

For each `(date, ticker)`:

```
trailing_high(d) = max(close[t] for t in the 252 trading days ending AT d)
drawdown(d)      = close(d) / trailing_high(d) - 1        # <= 0
dip20(d)         = drawdown(d) <= -0.20
dip30(d)         = drawdown(d) <= -0.30
```

* **Point-in-time:** only closes with `t <= d` enter. Nothing after `d` is read. **C3 pins this by
  a source-level test and by a synthetic panel where a post-date crash must not move the flag.**
* **THE PRICE BASIS IS THE TRAP AND IT IS COMMITTED NOW: the drawdown is computed on the
  SPLIT-ADJUSTED close, never a raw one.** A 2-for-1 split on an unadjusted series reads as an
  instantaneous **−50% drawdown** and would flag every splitting name — which, since companies split
  after they rise, would flag the strongest names in the universe and invert the entire feature. The
  session-30 rule (`raw_close` for anything touching a STRIKE, `close` only for a RETURN) applies
  here in its second half: **a drawdown is a return-like ratio, so adjusted is correct.** `SEP` is
  already split-adjusted, so `data/backtest/prices/*.csv`'s `close` is the right column. **C5 pins
  it with a synthetic 2-for-1 split that must produce NO dip flag.**
* **No per-ticker tail.** Prices are read whole (audit B6: `days=None`), never `.tail(N)`.
  **C6 pins it.**

### 3.3 The conditioning floors — fixed, untuned, and the ONLY values tested

```
quality_ok(d, i) = quality_theme_z(d, i) > 0.0        # the cross-sectional mean; the untuned midpoint
health_ok(d, i)  = health_score(d, i) >= 50.0         # the shipped 0-100 scale's midpoint
conditioned      = dip(d, i) AND quality_ok AND health_ok
```

* `quality_theme_z` is the panel's own `quality` column, exactly as scored — not rebuilt.
* `health_score` is `scoring.py::_health_score`'s arithmetic on point-in-time SF1 inputs, with the
  **breakpoint tuples and `_lerp` IMPORTED from `scoring.py`**, never retyped. Re-implementing a
  shipped mapping is audit **B7**'s defect class and S10's C2 is the precedent for importing it.
  The non-cash-burner branch is used (`lev` 0.5, `cov` 0.3, `fcf_ok` 0.2); the cash-burner branch
  needs `cash_runway_years`, which is a live-engine quantity, and **C4 records how many rows that
  affects rather than silently routing them.**
* **Both floors are scale midpoints. Neither was chosen by looking at an outcome, and NO OTHER FLOOR
  IS TESTED.** Sweeping a floor is a grid search on the panel that scores the result — the
  +8.43%/yr in-search → −0.04%/yr locked hold-out failure this project has already paid for. **A
  swept floor is void condition 6.3.**

### 3.4 Arms — four, fixed

| arm | depth | horizon |
|---|---|---|
| A1 | 20% | 63d |
| A2 | 20% | 126d |
| A3 | 30% | 63d |
| A4 | 30% | 126d |

The task fixes the depths (*the tab's default 20%, plus 30% as the only other arm*) and the horizons
(*63d/126d*). **No fifth arm exists and adding one is void condition 6.2.**

### 3.5 The two legs, and which one carries the claim

Per rebalance date `d`, on equal-weighted means of the horizon's forward return:

```
L1(d) = mean(fwd | conditioned) - mean(fwd | ALL panel names)          # "better than the market"
L2(d) = mean(fwd | conditioned) - mean(fwd | dipped, UNCONDITIONED)    # "the QUALITY is what does it"
```

**L1 is the tab's literal sentence. L2 is the one that decides whether the sentence is honest.** L2
is the control the task names — *the control that separates "healthy dip" from "any dip"* — and by
§1e it is also the leg immune to the flag's violent time-variation, because **both sides of L2 are
dipped names on the same date**.

**VERDICT RULE, fixed now:**

> An arm is **POSITIVE** iff **BOTH** legs clear **their own** permutation p95 in **BOTH** halves,
> with the **same sign in both halves** on both legs.
>
> An arm that clears **L1 but not L2** is **NULL, and is reported as "the dip is doing the work,
> not the quality"** — that outcome specifically forbids the tab's copy, because the copy claims the
> conditioning.
>
> An arm whose **L2 is significantly NEGATIVE** (below the permutation p5, both halves) is
> **REJECTED — SIGN REVERSED**: quality conditioning actively *hurts* a dip. This is a real possible
> outcome (S10 found a valuation screen deleted names that outperformed and crashed *less*) and it
> flips the copy hardest of all.
>
> Ambiguous against any bar is a **NULL**, never a judgement call (`RUN_RULES` A6).

### 3.6 Inference and the bar

* **Statistic:** the per-date series `L1(d)`, `L2(d)` over the 69 dates, summarised by
  **`statistics.mean_inference`** — M2 made that the single shared definition, and the four
  hand-rolled copies in `fundamental_panel` delegate to it. It is **not** re-implemented here.
  `n_eff` travels with `n` (M2's third requirement).
* **The bar is each leg's OWN within-date permutation p95, 500 draws, seeds banked.** Not X7's
  floors: X7 calibrated a **decile-book long-short t** and a **top-decile alpha margin**, and this
  is neither object. Quoting 2.2837 or 1.95pp here would be the uncalibrated-extrapolation error
  X3 and session 10 both paid for. **The permutation schemes differ per leg, deliberately:**
  * **L1's null** shuffles the `conditioned` flag among **all names on that date**, preserving the
    per-date count. It asks: does *any* set of this size beat the universe as much?
  * **L2's null** shuffles the `quality_ok AND health_ok` labels **among the dipped names only**,
    preserving the count. It asks: does the *quality label* add anything beyond having dipped?
  * The `placebo_panel` machinery is **not** used. Per the recorded finding, it is exactly invariant
    on the composite and cannot calibrate a score-shaped object; these are within-column schemes.
* **Halves:** the 69 dates split into early/late with the boundary date **embargoed**, as every
  held-out gate in this project does.
* **Two-sided** on L2 (a reversal must be detectable — see §3.5); **one-sided** on L1, because the
  tab's claim has a direction and a significant *negative* L1 would mean dips underperform the
  market, which is not this hypothesis.

### 3.7 Coverage floors — a VOID, not a NULL

Per arm: **≥ 10 conditioned names per date**, and **≥ 24 covered dates in EACH half**. An arm
failing either is **VOID — UNDERPOWERED BY CONSTRUCTION**, reported as such and explicitly **not**
reported as a null. §1e says both depths should clear this comfortably; the floor exists so that if
the conditioning turns out to bite much harder than the depth alone, the arm says so instead of
returning a number computed on six names.

**The minimum detectable effect (`2 × se`) is computed and reported for EVERY arm, cleared or not.**
V2G's lesson, restated by S19: **NULL means "could not be separated from zero at this resolution",
never "absent"** — and S19's A1 sat *below its own detection threshold*, which is the only reason
its null was interpretable. Any null here that is quoted without its MDE is being misquoted.

---

## 4. Expectations, with odds, written before any result

This project's directional calls have been wrong more often than right, which is exactly why they
are written down first.

1. **All four arms NULL.** 70/30. The base rate here is overwhelming and the prior in §1a, though
   weakened, points the same way.
2. **L1 will look better than L2 on at least three arms.** 75/25. A dip is a value/low-momentum
   tilt, and R1 measured this book already carries HML +0.251 and UMD +0.205; the universe
   comparison should pick some of that up while the dipped-vs-dipped comparison cannot.
3. **The quality conditioning removes far more names than the health floor does.** 60/40. `quality`
   is a 10-input z-scored theme with roughly half the cross-section above 0 by construction; the
   health floor at the scale midpoint should be looser than that.
4. **At least one arm trips the L2 sign-reversal branch in at least ONE half.** 55/45. S10 found a
   valuation screen preferentially deleted names that crashed *less*; a quality screen on a dipped
   set is a close cousin.
5. **126d shows a larger effect than 63d, on both legs.** 55/45. S22 measured the composite's
   out-of-sample rank IC *rising* with horizon (+0.034 → ~+0.072) and top-decile alpha still
   accruing at two years.
6. **The 30% arms are noisier and NOT better.** 65/35. Fewer names, deeper distress.
7. **Drawdown and 1-month reversal correlate weakly — |ρ| < 0.4 (C7).** 60/40. They are different
   objects (§1a) and I expect the record to show it.
8. **Conditioned names are LARGER than unconditioned dipped names.** 60/40. Quality and health
   floors both tilt large in a megacap-heavy panel — U7's and S10's failure mode — and **C8 measures
   it precisely so a size sort cannot be reported as a quality finding.**

---

## 5. Controls

| id | control | gating? |
|---|---|---|
| **C1** | The harness reproduces the shipped record from its own panel build (`top_decile_alpha` 0.071741…, LS naive 2.83606…, HAC 2.61991…, monotonicity −0.890909) to ≥ 9 decimals. **GATING: runs in its OWN pass and ABORTS before any arm is scored if it fails.** Session 26's defect; repaired in S17 and kept. | **YES** |
| **C2** | Panel shape is canonical (~2,531 names, 69 dates, label `full`) — asserted, not warned. | **YES** |
| **C3** | Zero point-in-time violations: no close dated `> d` enters any trailing high; verified on a synthetic panel where a post-date crash must leave the flag unchanged. | **YES** |
| **C4** | Coverage first (COVERAGE RULE): conditioned/dipped/total counts per date per arm; how many rows would have taken the cash-burner health branch; and a hard assertion that `roic`/`roe` were **derived, not read** (§1c). | no |
| **C5** | Split trap: a synthetic 2-for-1 split on an otherwise flat series produces **NO** dip flag on the adjusted basis, and **DOES** on a raw one. Pins §3.2 from both sides. | no |
| **C6** | No per-ticker tail anywhere in the price read (audit B6), by source inspection. | no |
| **C7** | Correlation between `drawdown` and the panel's 1-month reversal / momentum inputs — the §1a "different object" claim, measured rather than asserted. | no |
| **C8** | Characteristic tilt: median market cap and mean `size` z of conditioned vs unconditioned-dipped vs universe. **A size sort must not be reportable as a quality finding** (U7, S10, S17's D1). | no |

**Every permutation draw is banked, not just the percentiles** (`RUN_RULES` A9 — X7's 100 draws
kept as five summary rates cost two sessions).

---

## 6. Void conditions

1. Any `.py` in the same commit as this file, or this file not being a strict ancestor of every
   measurement commit.
2. Any arm beyond the four in §3.4, or any depth or horizon other than 20/30 and 63/126.
3. Any floor other than the two in §3.3, or any sweep of either.
4. Substituting X7's calibrated floors for the per-leg permutation bars in §3.6.
5. Computing the drawdown on a raw (unadjusted) price series, or letting any close dated `> d`
   enter a trailing high.
6. A failing **C1**, **C2** or **C3** with any arm number nevertheless read or reported.
7. Editing this register after any arm result exists. Corrections go in the handoff, against the
   register, exactly as S17/S19's own §7 defect was handled.

---

## 7. Trial cost

**Four arms, four trials.** The two legs of an arm are a **conjunction producing one verdict**, so
they are one search, not two — the same treatment S14's decide/measure directions received.

**Equity `N` 202 → 206.** The 202 is **re-measured from `research_log.detail()` after this
session's own merge of `origin/main`**, not quoted from `CLAUDE.md` — that substitution is the exact
defect the S17/S19 register committed and corrected in its own handoff, and it is not repeated here.
(Options reads 287 and infra 11; both untouched by V6.)

`BACKTEST_RESULTS.json` is refreshed at the new denominator from a clean tree, so the artifact does
not go stale on `N`.

---

## 8. THE EXPLAINER CONSTANT — named now, before the tab can claim anything

The verdict flips one named constant either way, and it is named **here** so the tab cannot ship
copy that outruns it.

**`valuation/web/dip_confidence.py`** — modelled exactly on **`valuation/web/score_confidence.py`**,
which is the shipped precedent: V3 found the hot score NOT DISTINGUISHABLE, and that module became
the single source for the weakened wording, read by four surfaces and pinned **verbatim** to its
handoff by `tests/test_score_confidence.py`.

It carries, at minimum:

```python
SOURCE   = "HANDOFF_edge_audit.md"          # the V6 section
REGISTER = "PREREG_v6_dip_detector.md"
VERDICT  = ...        # one of: POSITIVE | NULL | NULL - THE DIP DOES THE WORK
                      #         | REJECTED - SIGN REVERSED | VOID - UNDERPOWERED
DEFENSIBLE = "..."    # the ONE sentence the tab is allowed to render
PER_NAME   = "..."    # an exact SUBSTRING of DEFENSIBLE, never a second rewrite of it
```

**What each verdict assigns, committed now:**

* **POSITIVE** → the tab may state the effect **with** §2's fidelity caveat attached, and may not
  quote a magnitude until the live-vs-panel check is done.
* **NULL** → the tab may describe the dip screen as **a filter, not a forecast**: it finds names
  that are down, and the project has **not** shown they recover better.
* **NULL — THE DIP DOES THE WORK** → the copy may not attribute anything to quality conditioning.
* **REJECTED — SIGN REVERSED** → the tab must say the conditioning is **not** supported and the
  screen should not be sold as improving outcomes.
* **VOID — UNDERPOWERED** → the tab says nothing about performance at all.

**The rule that makes this enforceable rather than decorative:** the sentences live in that one
module, are quoted verbatim from the handoff, and are pinned by a test that normalises whitespace
and fails if either side is reworded — the same mechanism `score_confidence.py` already uses, which
was mutation-tested at 4 of 4 drifts caught. **A product surface that "tidies" a calibrated sentence
is how a hedge quietly becomes a claim.**

**Ownership:** the constant and the tab are the **app lane's** to build. This register fixes the
verdict and the wording contract; it does not ship a web surface, and no file under
`valuation/web/` is touched by the measurement commits.

---

## 9. What this register does NOT test — named so it is not mistaken for tested

* **The tab's live sub-scores** (§1f, §2). Different objects.
* **Any floor other than the two midpoints** (§3.3).
* **Any drawdown window other than 252 trading days.** The trailing-high lookback is fixed at 252
  (the 52-week convention) and is **not** swept.
* **Whether to BUY on the signal.** This measures a forward return difference, gross of costs, on
  the panel. It is not a book, it has no turnover, and it carries no cost model.
* **P4-3's classic anomalies on the corrected universe** (§1a). Still open, still needs its own
  register.
