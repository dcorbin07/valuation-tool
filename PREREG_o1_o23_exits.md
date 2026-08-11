# PRE-REGISTRATION — O1 (exit sweep incl. random entries) + O23 (exits vs the underlying)

**Committed before any policy was scored or any decomposition computed.** Nothing below was
written with a result in hand. The one number quoted here — 3,885 of 3,885 contract histories
present in the freeze — is a mechanical instrument check (does the input exist), not a result;
it is stated because the study's feasibility depends on it and hiding it would make the
"replay from the frozen book only" gate unfalsifiable.

Author: options-bot lane, 2026-08-08. Audit items **O1** and **O23**.

---

## 0. WHY THIS IS NOT A RE-RUN OF THE 2026-08-03 EXIT LAB

`data/options_exitlab/EXITLAB_RESULTS.json` already exists, dated **2026-08-03**, and it already
carries a verdict: *"REJECT — the inherited exit is not beaten"*, 0 policies adopted, 0
signal-only, PBO 0.0754.

**That verdict is not transferable and is not cited as evidence here**, for three reasons that
are properties of the run rather than opinions about it:

1. **It ran on the pre-correction book.** 3,119 signal entries over 278 names, banked
   2026-08-03 — *two days before* the five R2 defects (B1 mis-stated underlying price, plus
   B2/B3/B4/B15) were repaired on 2026-08-05. B1 alone moved median entry IV from 1.4200 to
   0.2497 and moved the trade count 3,042 → 3,885, because an adjusted spot against as-traded
   strikes was throwing the moneyness prefilter. Every entry fill in that run is suspect.
2. **Its random control is not the R2 five-seed control.** 5,986 random entries against 3,119
   signal — a ratio near 2, i.e. roughly two draws, against the standing rule of five that R2
   established *after* a single seed nearly flipped the entry verdict.
3. **Its inputs are retired.** The 2026-08-08 chain-freeze reconciliation classified the exit
   lab's book as RETIRED — *inputs no longer reproducible* — so its paths cannot be re-derived
   even if one wanted to.

**I have seen that verdict before writing this.** That is stated plainly because it bears on
trial accounting: this re-run is **not blind**, so it is charged again rather than waived as a
repair, following the O16-REFROZEN precedent set on 2026-08-08.

**What is NOT re-opened:** the entry signal is dead (R2), and nothing here re-tests it.

---

## 1. THE OBJECT OF STUDY

**The 21 exit policies in `options_exitlab.POLICIES`, unamended.** They were fixed and committed
on 2026-08-03 before any policy was scored, and this pre-registration does **not** add, remove or
retune a single one. Their definitions, the fixed within-day check order (TARGET → STOP → TRAIL →
TIME), and the X1–X6 gate are imported from the module rather than restated, so they cannot drift.

**Entry sets — both replayed from the 2026-08-08 chain freeze and from nothing else:**

| set | book | trades | names | freeze |
|---|---|---|---|---|
| **signal** | `state_r2_corrected.pkl` | 3,885 | 186 | `data/options_freeze/R2_CORRECTED_2026-08-08/` |
| **random** | `control_r2_seed{0..4}.pkl` | 29,785 | — | `data/options_freeze/R2_CONTROLS_2026-08-08/` |

**Five seeds, pooled** (6032 / 5972 / 5904 / 5987 / 5890) — the standing R2 rule. Per-seed
figures are reported alongside the pooled ones so that a single-seed flip is visible rather than
averaged away; the R2 lesson is that one control draw nearly reversed a verdict.

Settlement is `settle="intrinsic"` — the exit lab's default and its own documented main finding
(a stale last-quote mark manufactures a monotone reward for holding longer). Headline aggression
is 1.0.

---

## 2. BLOCKING GATE G0 — THE REPLAY MUST COME FROM THE FREEZE

The brief is explicit: *"if any replay misses the freeze, that is a blocking finding, not a
footnote."* Two conditions, both blocking, both checked before any policy is scored:

* **G0a — completeness.** Every trade's selected contract history must be present in the frozen
  copy. *Measured mechanically before writing this: **3,885 / 3,885** on the signal side, zero
  missing, median 40 post-entry quote days, zero trades with no post-entry day.* The random side
  is checked the same way at run time. **Any missing contract stops the study for that set.**
* **G0b — fidelity.** The `shipped` policy, replayed from the frozen copy, must reproduce the
  banked book's own exit outcome: matching `exit_reason` **and** `pnl_pct` within 1e-6 on
  **≥ 99%** of trades — the same bar O16 used. This is the strong form of the check, because it
  tests the freeze, the path builder and the policy evaluator against a book none of them wrote.

**If G0b fails**, the study follows the O16 precedent exactly: it reports the blocker as the
finding, may report an exploratory read on the exactly-reproducing subset, and that read
**carries no verdict**. A blocked study is a result; a study that quietly scores the 86% that
happens to match is not.

**Underlying prices come from `data/bulk/prepared/bars/` (Sharadar SEP), which is a DIFFERENT
store and is NOT covered by the options freeze.** This is a real gap and it is declared here
rather than discovered later: O23 is the first study whose headline depends on the underlying
leg. The bars files consumed are fingerprinted and stamped alongside the results, so this run is
reproducible even though the gap predates it.

---

## 3. O1 — THE EXIT SWEEP

### 3.1 The gate (X1–X5, imported unchanged from `options_exitlab`)

A policy is **ADOPTED** only if all hold at aggression 1.0:

* (a) beats `shipped` expectancy by ≥ `MIN_EXPECTANCY_GAIN` = **0.10** on the **signal** entries;
* (b) **also** beats `shipped` on the **random** entries — the key test;
* (c) positive in **both** held-out halves on **both** entry sets;
* (d) ≥ `MIN_CLOSED_PER_BUCKET` = **30** closed trades;
* (e) its paired name-year advantage survives **BH-FDR at Q = 0.10** across all 21 policies;
* and **PBO < 0.50** by CSCV over the policy × time-block matrix, 10 blocks / 252 splits.

### 3.2 Which pattern counts as which — REQUIRED BY THE BRIEF, FIXED HERE

| beats `shipped` on | label | reading |
|---|---|---|
| **both** sets | **EXIT EFFECT** (ADOPT-eligible) | a property of the exit, entry-independent |
| **signal** only | **SIGNAL-ONLY** | entry information leaking through the exit; reported separately, never merged into a headline |
| **random** only | **CONTROL-ONLY** | explicitly **not** adopted — the shipped book is the object, and a rule that helps only random entries has no deployment path here |
| **neither** | **REJECT** | the inherited exit is not beaten |

**Ambiguous is a NULL.** A policy whose paired sign-test CI95 straddles zero on either set is
NULL for that set, and a NULL on either set forbids ADOPT.

### 3.3 Inference

* **The paired name-year sign test carries the verdict** — the standing R2 rule, distribution-free,
  and the statistic that survived R2's own control-seed fragility. Pooled expectancy is a
  diagnostic, not a verdict: on a barbell payoff it is set by a handful of +600% trades.
* **Date-block bootstrap**, block = calendar **month**, **2,000 draws, seed 0**, via
  `options_stats.date_block_bootstrap` / `date_block_diff`. Every interval quoted is clustered.
* Deflated Sharpe at `n_trials` = 21 policies; per-seed spread reported.

### 3.4 Expectation, written down first

**I expect REJECT — no policy clears both sets — at 70/30.** The shipped exit was never tuned, so
it is a fair rather than an overfitted baseline, and this project's directional expectations have
been wrong more often than right (R10, O20, the spread toll, U7). Writing it down is worth doing
precisely because it keeps being wrong.

---

## 4. O23 — EXITS MEASURED AGAINST THE UNDERLYING

### 4.1 The decomposition

Every policy shares the **identical entry**; policies differ *only* in when the position is
closed. So for trade *i* and policy *P* against baseline `shipped` *S*:

```
Δ_opt(i,P) = R_opt(i,P) − R_opt(i,S)     option return difference
Δ_und(i,P) = R_und(i,P) − R_und(i,S)     underlying simple return over the same two holding periods
```

where `R_und(i,X)` is the as-traded underlying return from the entry date to policy X's exit date.

**Restriction, fixed here:** only trades whose policy exit date **differs** from `shipped`'s are
scored. Including identical exits would pad the sample with (0, 0) pairs and inflate R² toward 1
mechanically. A policy with fewer than 30 such trades is not scored.

### 4.2 Primary statistic

Per policy, OLS `Δ_opt ~ a + b·Δ_und`; the statistic is **R²_und**, the share of the exit rule's
P&L difference that the underlying's move alone reconstructs. Date-block CI95 (month, 2,000
draws, seed 0). Headline is the **pooled** regression over all (trade, policy) pairs; per-policy
figures ship alongside.

### 4.3 Secondary statistic — Greek attribution

Over the interval between the two exit dates, attribute the option's mark change using Greeks
evaluated at the interval's start, from `options_greeks` on the frozen chain's own quotes:

```
ΔV  ≈  delta·ΔS  +  ½·gamma·ΔS²  +  vega·Δσ  +  theta·Δt  +  residual
```

Implied vol is solved at **exit dates only** (not every day of every path) — sufficient for an
interval attribution and the reason this arm is affordable. Mean share of each term is reported.
**This arm is secondary and carries no verdict on its own**; it exists to say *which* option-specific
component matters when the primary says the underlying does not explain the difference.

### 4.4 Verdict rule

| condition | verdict |
|---|---|
| R²_und ≥ 0.50 **and** CI95 lower bound ≥ 0.50 | **UNDERLYING-DRIVEN** — the exit ladder is a stock holding-period study in options costume |
| R²_und ≤ 0.25 **and** CI95 upper bound ≤ 0.25 | **OPTION-DRIVEN** — the differences are vol/theta, genuinely optiony |
| anything else | **NULL** (mixed / not separable) |

**The verdict is stated on the SIGNAL book.** The random book is scored identically; **if the two
sets disagree on the label, the verdict is downgraded to NULL** and reported as set-dependent.
A one-sided near-miss is a NULL, not a "nearly".

### 4.5 Expectation, written down first

**I expect UNDERLYING-DRIVEN at 60/40.** A long call held longer is mostly a longer bet on the
stock, and theta is a drag rather than a source of cross-sectional dispersion. Recorded so it can
be scored against the outcome.

---

## 5. TRIAL ACCOUNTING, COMMITTED IN ADVANCE

* **O1: n=21** — the 21-policy grid, one pre-registered sweep. Charged in full even though the
  policies were fixed in 2026-08-03, because the 2026-08-03 verdict was read before this run
  (O16-REFROZEN precedent: a re-run that is not blind is charged again).
* **O23: n=2** — the primary regression and the Greek attribution.
* Both to the **options** domain. **Equity `N` is untouched at 129**, so no equity claim moves.
* Rows go to `RESEARCH_LOG.md` with the verdict column clean and every `|` inside a cell escaped
  as `\|` — Session 12's parser counts a misaligned row toward a *larger* N, and my own lane
  produced the only malformed row in 74.

---

## 6. WHAT THIS STUDY CANNOT SEE — inherited, and not repaired here

* **Daily closes only.** An intraday spike through a target or trail that closes back inside is
  invisible. This bites the TRAILING policies hardest, so trailing results are optimistic.
* **No true ATR** — the bars carry date/close/volume, no high or low.
* **Trade-scope freeze**, so this can replay the exits of a given book; it cannot re-derive
  *which* alerts fire. O1 is an exit study by construction and does not need that, but no
  conclusion here may be extended to entry selection.
* **The universe is the miner's cache**, screened by today's liquidity. Both biases run toward
  the edge surviving and neither is removable here.
* **No early exercise, assignment or borrow.** Long calls only.
* Per-day expectancy is not a portfolio return; sizing is a different thread.
