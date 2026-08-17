# PREREG — P1 Stage 0: does the equity composite still sort the PIT-OPTIONABLE universe?

**Committed ALONE, before any arm is scored.** One `.md`, zero `.py`. This file is a strict git
ancestor of every measurement commit; if it is not, the register is void and the run may not be
reported (`RUN_RULES` A2).

**Item:** `VALQUO_OPTIONS_FRONTIER.md` §3 P1 Stage 0 — *"the gate, and it runs alone."*
**Charged to EQUITY, not options.** Every arm predicts the UNDERLYING's forward return, which is
the `U2`/`MA31` precedent for domain assignment. **Equity `N` 227 → 230. Options `N` stays 292.**

**ADOPTS NOTHING.** No file under `valuation/edge/`, `valuation/screener/` or `valuation/web/` is
edited. The measurement module is a study (`valuation/studies/`), which may import the engine and
never the reverse (`tests/test_studies_boundary.py`).

---

## 0. Premise facts — MEASURED FOR THIS REGISTER, not inherited from the frontier

The frontier document is a read-only design written by a separate session. Its claims are
verified here rather than adopted. Everything in this section was measured **before** this file
was written and **none of it touches a forward return on a restricted universe** — that is the
arm, and it waits.

**ORDERING, STATED PLAINLY BECAUSE IT IS THE THING A REGISTER EXISTS TO GUARANTEE.**
`valuation/studies/optionable_universe.py` and the partition artifact it builds were also
written **before** this file, and they arrive in the measurement commit rather than this one so
that this commit stays `.md`-only. That is disclosed rather than hidden because it is
load-bearing: a universe definition built before the register could in principle have been
tuned to an outcome. It could not have been here, and C2 is the proof rather than the promise —
the partition is a pure function of (date, ticker, chain) and **never reads a forward return**,
asserted at source level and behaviourally. **No arm has been scored on any restricted universe
at the time of this commit**, which is the claim that actually matters.

**0a. The panel is what the frontier says it is.** `data/free_analysis/panel_s22_h504.pkl`:
**113,945 rows × 24 cols, 2,531 names, 69 dates, 2009-01-15 → 2026-01-28**, carrying all eight
forward-return columns `fwd_ret`, `fwd_ret_h{126,189,252,315,378,441,504}`. Theme coverage
reproduces `CLAUDE.md` exactly (`institutional` 0.7172, `insider` 0.8308, `sentiment` 0.0000).

**0b. THE SHIPPED INSTRUMENT REPRODUCES THE RECORD AND THE FRONTIER'S DOES NOT — this is why
Stage 0 exists at all.** Running S22's own `arm()` (which wraps the shipped `quantile_backtest`
on the deployed weights) at H=63 on the full panel against S22's committed `C1_RECORD`:

| field | published | measured | \|Δ\| |
|---|---|---|---|
| `top_decile_alpha` | 0.071741423321 | 0.071741423321 | **1.84e-14** |
| `long_short_tstat` | 2.8360640685320595 | 2.8360640685320595 | **0.00e+00** |
| `monotonicity` | −0.8909090909090909 | −0.8909090909090909 | **0.00e+00** |
| `equal_weight_ann` | 0.18137118752419476 | 0.18137118752419476 | **0.00e+00** |
| `long_short_tstat_nw` | 2.6199 | 2.619912124041 | 1.21e-05 |
| `top_decile_alpha_tstat_nw` | 4.3762 | 4.376230427940 | 3.04e-05 |

The two 1e-05 residuals are `C1_RECORD` storing those fields to four decimals; both reproduce to
the precision recorded. **The frontier's own instrument reached +7.48% against +7.17%** and it
said so, calling that *"close enough to scope a decision and not close enough to publish."* It
was right. The difference is not cosmetic: its composite used `nlargest(len(g)//10)` where the
shipped `quantile_backtest` uses `np.array_split(order, n_q)`, so the two do not even hold the
same names. **Nothing from frontier §2d or §2e is quoted as a result anywhere in this register.**

**0c. The chain cache spans 2016-2025 ONLY, so most of the panel has no point-in-time chain.**
1,000 raw ticker directories (**a correction: the frontier says 1,044; that count includes 44
non-directory entries**), **906 of which are names in the equity panel**, 26.98 GB. Cached years
are exactly `[2016 … 2025]`. **40 of 69 panel dates fall in a cached year**, first 2016-01-20.

**0d. THE GEOMETRY IS THE BINDING CONSTRAINT AND IT DECIDES THE DESIGN.** Intersecting cached
years with each horizon's right-censoring:

| horizon | cached & scorable dates | halves | HAC lag | window overlap | ≈ independent obs |
|---|---|---|---|---|---|
| **H=63** | **40** | 20 / 20 | 1 | **0.0%** | **40.0** |
| H=252 | 38 | 19 / 19 | 3 | 75.0% | 9.5 |
| H=504 | 34 | 17 / 17 | 7 | 87.5% | 4.2 |

**At H=504 the entire restricted sample carries about four independent observations and each
half about two.** That is `SELRULE`'s situation — a design whose rejection region may be empty —
and it is why §4 below fixes a three-state verdict grammar *before* any number exists, and why
**H=63 is added to the frontier's specified H=252/H=504 as the power anchor**. H=63 is the only
horizon at which a null is interpretable, because it is the only one with independent periods.

**0e. A full-panel both-halves gate is IMPOSSIBLE, not merely weak.** Every covered date is
2016 or later on a panel starting 2009-01-15. This is exactly `S18`'s, `U2`'s, `U3`'s,
`V6-OPT`'s and `MA31`'s situation for the sixth time, and the replacement is the same: **every
split in this register is of the COVERED SUBSAMPLE.** A pass on 17-date halves is not the same
object as a pass on 34-date halves, and is never reported as one.

---

## 0.5 NON-BLINDNESS, DISCLOSED HERE RATHER THAN AFTER — the `U3` §0.5 precedent

**I am not blind to the expected direction of this result.** `VALQUO_OPTIONS_FRONTIER.md` §2d is
on `origin/main` and reports, on a today-optionable partition with a non-reproducing composite,
top-decile alpha of **+17.52% at H=504 on optionable names against +10.59% on the full panel**.
I read it before writing this file. Pretending otherwise would be worse than declaring it.

Three things follow, and they are the reason this register can still be worth anything:

1. **THE BAR IS NOT MINE AND WAS NOT CHOSEN AFTER SEEING THAT NUMBER.** §4's primary bar is
   quoted **verbatim** from the frontier's own §3 P1 Stage 0, written by a separate read-only
   session and committed at **`d85299a`** — a git object predating this register. Leaning on an
   externally pre-stated bar is `U3`'s remedy for exactly this situation.
2. **THE PARTITION IS THE THING THE FRONTIER GOT WRONG, AND IT IS BUILT BEFORE THE ARM.** Its
   §2d used optionability measured **today**; it flagged that itself as *"a survivorship tilt in
   exactly the flattering direction."* The whole point of Stage 0 is that this correction may
   move or destroy the number. So knowing the uncorrected value tells me little about the
   corrected one, and the direction of the correction is known in advance to be **against** the
   result.
3. **A DECISIVE FAIL IS AVAILABLE AND A DECISIVE PASS IS NOT.** See §4's asymmetry clause.

---

## 1. The universe — one primary, one sensitivity, named before either is scored

`valuation/studies/optionable_universe.py` maps each (rebalance date, ticker) to whether the
option miner's **own** screen would have admitted that name **on that day**, by importing
`pit_liquidity` / `pit_liquid_ok` from `valuation/edge/options_universe.py` (audit O20), which
in turn imports the miner's constants. **No threshold is re-typed anywhere in this lane.**

* **PRIMARY — `pit_liquid`.** The cache holds a chain dated within `STALE_MAX_DAYS = 5` on or
  before the rebalance date, **and** O20's screen returns `True` on it. This is the universe P1
  would actually have to trade, which is why it is primary.
* **SENSITIVITY — `has_chain`.** Any point-in-time chain at all, screen ignored.
* `pit_liquid_ok` is **tri-state**: `None` when the day's chain cannot answer. An unmeasurable
  day is excluded from the primary and included in the sensitivity. Neither choice is neutral,
  so both are reported.

**ON-OR-BEFORE, NOT STRICTLY-BEFORE, AND THE DISTINCTION IS DELIBERATE.** *"Does this name have
a tradeable chain today"* is contemporaneous information observed at the rebalance close, like
every price the panel already uses; it is not a forecast. `join_pit`'s strictly-before rule
governs **predictive features**, and a chain's existence is not one. `staleness_days` is stored
on every row so the choice is auditable, and C8 reports how often it is non-zero.

**THE RESIDUAL SELECTION THIS CANNOT REACH, STATED NOW SO NO RESULT IMPLIES OTHERWISE.** O20's
own correction records that the mining **pool order is hindsight** — names were ranked by
TODAY's market cap, so a name liquid in 2016 that has since died was never cached. **No
evaluation-time filter recovers data that was never mined.** This partition therefore fixes the
*dating* of optionability and cannot fix the *name selection*. **A pass means "the composite
sorts the names we mined, dated honestly", never "the composite sorts optionable names."** That
sentence must travel with any positive result from this register.

---

## 2. The arms

Scored by S22's `arm()` → the shipped `quantile_backtest`, deployed weights
(`value/quality/momentum/insider/capital_discipline/size/institutional` at 0.125 each,
`low_risk` zeroed), `n_q=10`, `ret_col=fwd_ret_h{H}`, HAC lag `max(1, H//63 − 1)`.
**Deciles are re-ranked WITHIN the restricted universe**, which is the right construction for
*"trade the best of what is optionable"*.

| arm | horizon | role |
|---|---|---|
| **A63** | 63 | **POWER ANCHOR.** 40 dates, zero overlap. The only horizon where a null is interpretable. |
| **A252** | 252 | Gate, per the frontier. |
| **A504** | 504 | Gate, per the frontier. The horizon P1's instrument actually needs. |

**Primary statistic:** `top_decile_alpha_t_hac` — the top decile's per-period alpha over the
equal-weighted universe **of the same restricted cross-section**, HAC-corrected at the lag the
overlap induces. Reported beside it: `cum_alpha`, `alpha_ann`, `monotonicity`, `n_periods`.

**The long-short leg is measured and carries NO verdict**, per S22's own rider: *"nobody may
quote a long-short figure beyond about one year."* P1 is long-only by construction.

---

## 3. Controls — the gating ones run and are READ in their own pass

Session 26's defect (a gating control computed in the same pass as the outcomes) is not
repeated. `--controls-only` exits before any arm is scored, and the arms stage **refuses to run
without a passing controls artifact** — the `O19` two-pass design.

**GATING (a failure aborts before any arm is read):**

* **C1 — the instrument is the shipped one.** `arm()` on the full panel at H=63 must reproduce
  `C1_RECORD` to the precision recorded (measured: worst \|Δ\| **3.04e-05**, limited by the
  record's own 4-dp storage; the three exactly-stored fields reproduce at **0.00e+00**).
  Already measured in §0b; re-run and re-read in the controls pass.
* **C2 — the partition cannot see an outcome.** `optionable_universe.py` must contain no
  reference to any `fwd_ret*` column, asserted at source level **and** behaviourally: rebuilding
  the partition from a panel whose forward returns have been overwritten with noise must return
  a **bit-identical** partition.
* **C3 — PLACEBO VACUITY. The placebo must MOVE the number.** If a permuted draw's alpha equals
  the real alpha, the null is inert and its p95 is meaningless. This is not hypothetical: the
  project has recorded that `placebo_panel` is *exactly invariant* when pointed at an already
  computed score column. Here the composite is rebuilt from permuted theme columns each draw, so
  it should bite — and that is asserted rather than assumed.
* **C4 — no forward return is permuted.** S22's own leak guard (`placebo` raises if any
  `fwd_ret*` appears in `placebo_signal_cols`), re-run here.
* **C5 — the restriction is not inert.** The restricted universe must be materially smaller than
  the full panel and its decile membership must differ. A "restriction" that changes nothing
  would make every arm a re-run of the published headline wearing a new name.

**REPORTED (no verdict rests on them):**

* **C6 — COVERAGE FIRST**, per the COVERAGE RULE: dates with any chain, dates with a
  `pit_liquid` name, median names per covered date, share of the panel cross-section, and the
  count of unmeasurable days — all read **before** any return is scored.
* **C7 — the null is centred near zero** (S22's C4). A null centred away from zero means the
  instrument is broken, not that the effect is large.
* **C8 — staleness.** Max and non-zero share of `staleness_days`.
* **C9 — MDE.** The minimum detectable alpha HAC *t* at each horizon's own placebo p95, and
  whether the observed effect reaches it. **Quoted against the MEAN, not the median** — `MA31`'s
  third defect was pairing an MDE with the wrong statistic, and it is not repeated.
* **C10 — the size confound.** `MA32` and `U7` both found that inside a narrow optionable slice
  the composite decile is largely a market-cap sort. The restricted universe's decile is
  measured for market-cap tilt (median cap of D1 vs the restricted universe). **Reported, no
  verdict** — a size tilt does not invalidate a long-only alpha, but a reader must know whether
  the gate passed on `size`.

---

## 4. Verdict — THREE states, fixed before any number exists

The frontier's bar, quoted **verbatim** from `VALQUO_OPTIONS_FRONTIER.md` §3 (commit `d85299a`):

> *"Pre-commit the bar before looking: top-decile alpha on the PIT-optionable universe at H=252
> and H=504 must clear its own per-horizon `placebo_panel` floor (200 draws, the S22 protocol)
> **in both halves**. Kill condition: if it fails, the entire family dies here and no option is
> ever priced."*

Operationalised, on the **PRIMARY** (`pit_liquid`) universe, boundary embargoed:

* **PASS** — `alpha_t_hac` clears its own per-horizon `fixed_weights_null` p95 (200 draws,
  computed on the **restricted** universe, S22's `placebo` protocol) in **both halves**, at
  **both** H=252 and H=504.
* **FAIL** — it does not clear, **and** the observed effect exceeds its own MDE (C9), i.e. the
  design could have seen an effect of that size and did not.
* **UNDERPOWERED** — it does not clear and the observed effect sits **below** its own MDE. Per
  the standing rule (`S19`, `V6`, `MA31`), that reads *"could not be separated at this
  resolution"*, **never** *"absent"*.

**WHICH STATE FIRES THE KILL CONDITION — decided now, not after.**

* **FAIL at A63 → THE FAMILY CLOSES.** H=63 has 40 independent periods and is the horizon where
  this design has real power. A genuine failure there closes P1, P3, U6 and every future
  "express the equity book in derivatives" item, exactly as the frontier specifies. **That is a
  good outcome and it is cheap.**
* **FAIL at A252/A504 with A63 passing → PARTIAL.** The family is **not** closed, and P1 Stage 1
  may not claim long-horizon support. The `S10` precedent: a row closed `PARTIAL` because half
  of it was never tested, rather than `DONE`.
* **UNDERPOWERED anywhere → carries no verdict at that horizon** and may not be reported as
  evidence in either direction.

**THE ASYMMETRY, DECLARED IN ADVANCE.** At H=504 the restricted sample holds ~4 independent
observations and one market regime boundary. **A decisive FAIL is available at A63; a decisive
PASS at A504 is not.** Nobody may read a PASS here as evidence that the composite works at two
years on optionable names — at that horizon this design can only fail to reject.

**THE SENSITIVITY UNIVERSE CANNOT RESCUE THE PRIMARY.** If `has_chain` passes where `pit_liquid`
fails, the verdict is the primary's and the gap is **recorded as a discrepancy, not a verdict**.
It charges no trial precisely because it cannot produce one. Two shots at one bar is what this
clause exists to prevent.

---

## 5. Void conditions

1. This file is not a strict git ancestor of every measurement commit.
2. Any threshold, horizon, universe definition, weight vector or verdict rule above is edited
   after a number is read. Corrections go in the write-up; **the register is left unedited**.
3. A fourth horizon, a second partition rule, a different staleness window, or any additional
   arm is scored. The grid is `{63, 252, 504} × {pit_liquid primary, has_chain sensitivity}` and
   nothing else. Searching staleness windows until one clears is the defect this forbids.
4. `EDGE_AUDIT_B7_LEGACY_COMPOSITE` or any other attribution toggle is set.
5. A gating control (C1–C5) fails and an arm is reported anyway.
6. The `pit_liquid` / `has_chain` thresholds are re-typed in this lane instead of imported from
   `options_universe`, or the miner's fallback copy is silently used (its `source` field is
   recorded in the artifact).
7. Any figure from `VALQUO_OPTIONS_FRONTIER.md` §2d or §2e is quoted as a result of this run.

---

## 6. Trial accounting

**Equity `N` 227 → 230.** Three arms (A63, A252, A504), each of which could independently have
been reported as a positive finding. The sensitivity universe charges **zero** (§4). The
controls charge zero. **Options `N` stays 292** — no options contract is priced in Stage 0.

`tests/test_research_log_integrity.py::EXPECTED_BY_DOMAIN` is updated to
`{"equity": 230, "options": 292, "unified": 0, "infra": 15}` **in the same commit as the log
row** (MA13's tamper-evidence: the change must appear in the diff).

**NO CIRCULARITY, CHECKED NOT ASSUMED.** `MA19` records that charging a trial can invalidate a
recalibration because `N` is an input to the floors being computed. It does not apply here: the
bars in §4 are a `fixed_weights_null` placebo computed fresh on the restricted universe, and
S22's `arm()` uses **fixed** weights with no CPCV, so no `_trials_haircut` and no `N` enters any
number this register produces.

---

## 7. Expectations — written before any arm is scored, scored honestly afterwards

1. **A63 PASSES on the primary universe — 70/30.** §2d indicates it and H=63 has the power. The
   30 is `MA32`, which is a genuine warning: on the contract-level options sub-population the
   panel's own best signals could not be separated from zero.
2. **A504 does NOT return a decisive PASS — 75/25**, on power alone (~4 independent obs).
3. **At least one of A252/A504 comes back UNDERPOWERED rather than FAIL — 65/35.**
4. **The PIT correction REDUCES the optionable universe's advantage versus the frontier's
   today-optionable §2d figure — 80/20.** The tilt it removes is a survivorship tilt.
5. **The optionable decile is materially larger-cap than the full-panel decile (C10) — 85/15.**
   `U7` and `MA32` both found it; optionability tracks size mechanically.
6. **Coverage: median `pit_liquid` names per covered date lands between 150 and 450 — 60/40.**
   Stated so that a wild miss is visible as a miss.
7. **The `has_chain` sensitivity and the `pit_liquid` primary agree in verdict at H=63 — 75/25.**
8. **This register does NOT end with P1 being worth trading.** Stage 0 is a gate on whether the
   *question* is open, and O11 (a positive-expectancy options book that still lost money at
   realistic size) governs everything downstream.

---

## 8. What this register does NOT do — named so nothing is mistaken for done

* **It prices no option and settles no contract.** It is an equity measurement on an
  options-defined universe. Stage 1 is a separate register.
* **It does not re-open `U1`, `R2`, `U2` or `MA31`.** No option is used as a predictor anywhere.
* **It does not measure the financing spread (frontier §2c), deep-ITM spreads (§2b), or the
  200-DTE ceiling (§2a).** Those are Stage 1's and the re-mine's.
* **It does not resolve `D2`'s licence question.** No new data is pulled; nothing is mined.
* **It cannot fix the mining pool's hindsight ordering** (§1), and no result may imply it did.
* **It does not establish that options are the cheapest leverage.** That is P1's actual claim
  and it is three stages away.
