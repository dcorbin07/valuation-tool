# HANDOFF — Frontier Scout / Valquo Index construction, beyond cadence

**2026-09-30. SEVEN DRAFTS, SIX RANKED. No measurement, no arm, no outcome statistic, ZERO
trials.** `by_domain` untouched — equity **248**, options **310**, unified **0**, infra **20**,
re-read from `research_log.detail()`. Nothing under `valuation/` changed; nothing is adopted; no
register is committed. `PREREG_DRAFT_*` files are drafts and an executor must commit one **ALONE**
before it becomes a register.

**Two figures DERIVED this session rather than quoted, because `CLAUDE.md` records both rotting:**
equity hurdle **3.3206712** at N = 248, and the live vintage — **vintage 4, OPEN, opened
2026-08-13**, label *"no-trade band, width 0.30"*, **~48 days accrued**. Read from
`track_meter.VINTAGES`. **Never quote a vintage from a prompt or a handoff, including this one.**

---

## 1. THE RANKING, BY EXPECTED VALUE PER TRIAL

| # | draft | one line | trials | owned data? |
|---|---|---|---|---|
| **1** | `IC1` data-arrival-aligned grid | the only lever `S8` left open, against a banked reference distribution | 1 | yes |
| **2** | `IC7` coverage renormalisation | ~28% of rows are scored on a six-theme composite and 72% on a seven-theme one | 1 | yes |
| **3** | `IC3` re-entry cooldown | the shipped band has an exit threshold and no entry delay | 1 | yes |
| **4** | `IC4` split cadence | themes decay at rates spanning 8.4× and share one clock | 1 | yes |
| **5** | `IC5` breadth at capacity | one arm, WIDER, against the measured crowding point | 1 | yes |
| **6** | `IC6` large-cap cut | the record predicts this one, and predicts it unfavourably | 1 | partly |
| — | `IC2` drift trigger | **WITHDRAWN from the ranked set**: free kill likely closes it, and it may be r1's | 0 | yes |

**Why "expected value per trial" ranks them this way.** Essentially everything in this record
rejects — 248 equity trials, overwhelmingly null — so per-trial value is dominated by four things,
not by how exciting the hypothesis sounds: whether a **free pre-outcome kill** can close it for
nothing; whether a **banked reference distribution** exists so the bar is calibrated rather than
invented; whether the **mechanism is measured** in the record rather than assumed; and whether it
needs **no rebuild**. `IC1` and `IC7` score on all four.

## 2. RUN `IC1` FIRST, AND THE REASON IS A NUMBER NOBODY HAS EXPLAINED

**`X2` measured seven equally valid rebalance grids and got long-short *t* of 2.703 / 2.836 /
2.850 / 2.926 / 3.374 / 3.410 / 3.517 — a spread of 0.814 of a *t* on the project's headline
statistic — and the record offers no mechanism for it.** `CLAUDE.md` carries the consequence as
*"quote t 2.7–3.5 depending on grid, straddling the hurdle"* and stops there. That is the largest
unexplained sensitivity in the construction, it sits on the one parameter nobody chose, and it is
cheap to probe.

Three further reasons it goes first:

1. **`S8` closed the cross-sectional lever and named this one in doing so.** `days_since_13f` takes
   **1.25 distinct values per date** (within-date sd **2.054 days**) because 13F quarter-ends are
   common calendar dates, so `S8` concluded staleness *"is common across names, not
   cross-sectional — so decaying it cannot re-rank anything."* **A common-mode exposure is
   untouchable by a weight and touchable only by moving the DATE.**
2. **It has a free null distribution.** `X2`'s seven grids are an empirical distribution of
   arbitrary phase choices, so the secondary bar is a percentile of them rather than a number
   chosen after the fact. With n = 7 the resolution is poor and the draft says so.
3. **One arm, one trial, no rebuild, no purchase, and the operational path already exists** —
   `REBAL-FRESH` shipped `REBALANCE_MAX_STALE_DAYS = 2` **trading** days and made
   `append_rebalance` read the book's own as-of date against the event date, so the live pipeline
   already distinguishes the two.

**The strongest objection, carried in `IC1`'s own §3:** `S9` found **no freshness gradient** —
top-decile forward return by filing-age quartile runs **+6.15% @38d, +6.12% @66d, +6.66% @71d,
+6.35% @88d**, with **Q1 − Q4 = −0.78%/yr**, the stalest quartile slightly ahead. The distinction
the draft rests on is that `S9` measured the **fundamental** axis (86.81 distinct values per date)
and the 13F axis has **1.25** — so `S9` is structurally incapable of answering the phase question
and must not be read as having closed it.

## 3. THE SEEDS — KEPT OR DISCARDED

| seed | verdict | what changed |
|---|---|---|
| **(1) data-arrival dates** | **KEPT, ranked 1st** | sharpened: `X2`'s seven grids become the reference distribution, and `S8`'s common-mode finding becomes the argument FOR rather than against |
| **(2) drift trigger** | **KEPT but WITHDRAWN from the ranked set** | its free census probably closes it at zero trials, and it is a cadence question that may be r1's. Drafted in full so whoever owns it runs the kill for nothing |
| **(3) breadth 5% / decile / quintile** | **KEPT, reduced to ONE arm** | three cuts is a grid. Reduced to one, and **WIDER** not narrower, because `P1`/`P2` put capacity and the $5.1B crowding point against narrowing, and `B17` showed the narrow direction is already represented by the record's least trustworthy number |
| **(4) cap cut $5B/$10B/$20B** | **KEPT, reduced to ONE arm, ranked LAST** | three cuts would be three chances to find a flattering universe. Ranked last because the record predicts the direction and the two readings **conflict** — `U7` says compression at the top hurts, `regime_split` says the edge lives at the top |
| **(5) split cadence** | **KEPT, RE-ENGINEERED** | the seed's fast side needs a monthly panel; `MA33` prices that at ~3× per build **plus ~5–7 h of placebo recalibration**, since every `X7` bar becomes an extrapolation. **Slowing value/quality DOWN creates the same differential on the existing 69-date panel for nothing.** The fast side is named and declined |
| **(6) anything better** | **TWO found** | `IC3` re-entry cooldown (ranked 3rd) and `IC7` coverage renormalisation (ranked 2nd) |

## 4. GRAVEYARD CHECK — EVERY IDEA AGAINST EVERY CLOSED ITEM

Nothing here re-opens a closed item. The material differences, stated so a reader can check them:

* **`S14` band / `S14-WIDTH`** — swept the **EXIT** rank and closed it (interior optimum 0.30,
  third extension forbidden). `IC3` adds the **ENTRY** delay, which that sweep never varied.
  Checkable against `S14-WIDTH`'s own grid.
* **`S22` term structure** — its §7 states outright that cohort persistence is **NOT** "hold
  longer". `IC2` and `IC3` both carry that, and `IC2`'s free kill exists precisely because `S22`'s
  tenure numbers (median spell **one** rebalance, **70.6%** exactly one, retention **36.6%**) make
  a drift trigger either inert or the hold-longer family.
* **`S23` exit rules** — four challengers, all inside 0.4pp/yr, three of four flipping sign
  between halves; `C-NEVER` **−10.89pp/yr** with alpha collapsing **15.48% → 3.37%** by dilution.
  That is the measured end of the stale-book direction and both `IC2` and `IC3` are priced against
  it.
* **`S11` horizon ensemble** — rejected at **−4.22pp / −2.05pp**. `IC4` is distinct because `S11`
  blended two composites whose weight vectors correlate **+0.9013 / +0.9674** (largely one
  composite twice), while `IC4` changes the refresh **rate of individual themes** inside one
  composite at one horizon. `S11`'s real confound — the deviation came from using IC-proportional
  weights at all — is why `IC4` holds the deployed flat 1/7 fixed.
* **`S13` inverse-vol and `R1-VAR`'s ruling** — `IC5` is the one most at risk of winning on Sharpe,
  so it declares in advance that the verdict is on **alpha**, with Sharpe reported carrying no
  verdict. Don's ruling binds: a Sharpe gain bought with alpha is not worth having unless the
  Sharpe is bad, and at **0.5866** with IR **~0.88/yr** the antecedent does not fire. `S13`'s
  **1.76pp** giveaway sitting *inside* `X7`'s **1.8629pp** margin is why no arm here uses a
  non-inferiority framing.
* **`S15` / `SECTOR-NEUTRAL-B6` / `W-1`** — closed twice on measurement and then closed again on
  its own named re-open condition when `S25` supplied the dated map (`W-1`: Δalpha −1.01pp against
  −1.09pp, so the look-ahead was not what was killing it). **No draft here touches sector.**
* **`MC10` weighting** — *"can never be a hurdle claim"*: 80% MDE **≥ 1.01pp** against a **0.83pp**
  gross ceiling. `IC5` and `IC7` both inherit that warning as a **pre-outcome kill**: compute the
  ceiling, compare it to the MDE, and close at zero trials if unanswerable.
* **`S10` exclusion** — counterproductive, and the flagged names crash at **0.479%** against
  **0.832%**, i.e. **half** the rate of the names kept. **No draft here proposes an exclusion
  screen.** `S10`'s sector spread (**48.88%** Financial Services vs **15.79%** Industrials) is used
  as a kill input in `IC6`.
* **`V6` dips** — four nulls, and drawdown is substantially an inverse-momentum sort (ρ **+0.6642**
  with `momentum`). **No draft here conditions on a drawdown.**
* **`S5`/`S6`/`S13`/`S24`/`S27`** — five weighting arms, all rejected, CPCV's best challenger
  missing by **79×**. `IC4` and `IC7` both inherit that prior and both hold the weights fixed.
* **`S20`/`S21` standardisation** — `S20` rejected, `S21` not replicated. No draft changes the
  standardiser.
* **`B13`** — only **PARTIAL**: categorical screen holds, liquidity screen does not. Used as a
  kill input in `IC6`, and the ADV-aware cost model stays closed per the manager's §6.

## 5. WHAT EVERY DRAFT SHARES, SAID ONCE

* **Bar.** The shipped `holdout_compare_panels` **verbatim** — margins **> +0.25** long-short *t*
  **AND > +100 bps** top-decile alpha, **BOTH** halves, boundary embargoed, **BOTH** weightings.
  That is the gate `SECTOR-NEUTRAL-B6`, `S14`, `S15`, `S3`, `S16`, `W-1` and `MB20` all used;
  reusing it verbatim is what stops a bar being chosen after the fact.
* **MDE.** Every arm except `IC6` is a **paired within-panel difference**, for which **no
  calibrated floor exists** — `V2G` established it and `R1-VAR` re-confirmed it; `X7` calibrates
  LEVELS. So each register must measure **its own** paired HAC SE (`MB8`: never borrow one across
  perturbation sizes) and print the 80%-power MDE at crit 2.0 **labelled UNCALIBRATED** and at the
  derived hurdle. The record's two measured paired SEs bracket the likely range: `MB8`'s
  **0.1106pp** (small perturbation) and `V2G`'s **0.9354pp** (whole-theme swap).
* **Fidelity, and it ABORTS.** Each register reproduces the published record at max |Δ|
  **0.000e+00** — `top_decile_alpha` **0.07174142332098163**, LS naive *t* **2.8360640685320595**,
  HAC *t* **2.6199121240414884**, monotonicity **−0.8909090909090909** — before anything is
  compared. `MA28`'s C1 and `W-1`'s K4 both fired on their own first runs from scoring nine themes
  at a seven-theme weight, so this is a gate and not a formality.
* **Vintage.** **All six are vintage events on adoption.** Derive the vintage, never quote it.
  Rule 6 is the brake: a reset discards the accrued clock and buys nothing statistically, and the
  contract's meter has **13.3% power at 60 months**. So every eligible result is recorded
  **ELIGIBLE, NOT ADOPTED** and routed to Don — the research verdict and the adoption decision are
  separate, and five of the six would close a vintage that is seven weeks old.

## 6. NOT DONE, AND NAMED SO IT IS NOT MISTAKEN FOR DONE

No measurement of any kind was run. No panel was built, no artifact written, no outcome statistic
computed, no kill evaluated — **including the free ones, which are drafted but not run.** No
register is committed, so none of these is a register yet. `IDEAS_LEDGER.md` and `SEASON3_MAP.md`
are **not edited**. No trial is booked; `by_domain` is untouched at equity 248.

**The boundary with r1 is NOT resolved and is not mine to resolve**: `IC2` is drafted and withdrawn
pending it, and `IC1` is asserted to be orthogonal to `REBAL-CADENCE` (phase, not frequency) on the
grounds that every cadence must pick a phase — **if r1's item sweeps phase as well, `IC1` is r1's
and this draft should be withdrawn too.**

**One thing I could not check:** r1's `PREREG_DRAFT` is not on `origin/main`, so the overlap above
is argued from the brief's description of `REBAL-CADENCE` rather than from r1's own text.

## 7. FILES

`PREREG_DRAFT_ic1_data_arrival_grid.md` · `PREREG_DRAFT_ic7_coverage_renormalisation.md` ·
`PREREG_DRAFT_ic3_reentry_cooldown.md` · `PREREG_DRAFT_ic4_split_cadence.md` ·
`PREREG_DRAFT_ic5_breadth_at_capacity.md` · `PREREG_DRAFT_ic6_large_cap_cut.md` ·
`PREREG_DRAFT_ic2_drift_trigger.md` (withdrawn from the ranked set) · this handoff.

Drafts only. Nothing under `valuation/`, `scripts/`, `tests/`, `data/` or `D:\wrds` is touched.
