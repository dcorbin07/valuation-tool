# PREREG — STAGE-1 BATCH 3 — eight arms from the published literature

**EXECUTOR PASS on the Frontier Scout's `PREREG_DRAFT_stage1_batch3.md`.** The draft is **ACCEPTED
with SIX AMENDMENTS**, every one made **BEFORE any outcome exists** and every one carrying the
measurement that forced it. Accepting and amending are different things and both are recorded.

**COMMITTED ALONE** — markdown only, zero `.py`, a strict git ancestor of every commit that
computes an outcome (`RESEARCH_CHARTER.md` §3). **Trials are booked in a separate commit BEFORE
any runner exists.**

**THE BATCH IS EIGHT ARMS RUN AND ONE NOT RUN, AND `k` STAYS 9.** `C9` is `NOT RUN`; §0.1 amends
the draft's reasons for that and the amendment makes one of them weaker rather than stronger, so
it is recorded rather than quietly inherited.

---

## 0. THE AMENDMENTS, EACH WITH THE MEASUREMENT THAT FORCED IT

### 0.1 `C9` IS `NOT RUN` — AND ITS FIRST REASON IS DISSOLVED, ITS THIRD IS WEAKER THAN DRAFTED

The draft gives three reasons and calls the third decisive. **Measured, the first is now false and
the third is weaker than it reads; a fourth is added that neither of us had.**

**REASON 1 IS DISSOLVED, AND THE CORRECTION IS GENERAL RATHER THAN ABOUT `C9`.** The draft says
O-score *"needs a panel rebuild"* because `liabilities`, `assetsc`, `workingcapital` and `retearn`
are *"absent from `WRDSProvider._KEEP`"*. **All four are in `_KEEP` as of `CORRECTED-REBUILD` plus
addendum 2's fold-in — the allowlist carries 52 columns and every one of the nine source fields
the nine arms name resolves.** So no batch-3 arm is `NOT RUN` for a missing column, which is the
thing addendum 2 asked for.

**AND THE DEEPER CORRECTION: NO ARM EVER NEEDED A *PANEL* REBUILD FOR A RAW COLUMN.** Measured on
`UNIVERSE_BIAS_PANEL_full_v3.pkl` (289,659 × 90): **all nine of `capex`, `liabilities`, `assetsc`,
`workingcapital`, `retearn`, `ncfdiv`, `ncfcommon`, `fcf`, `ncfo` are ABSENT from the panel** —
`keep_numbers=True` carries the derived NUMBER columns (53 z-ables), not the export's raw fields.
An arm reads raw fields through **`fundamentals_history`**, which honours `_KEEP`. **So
*"this arm needs a panel rebuild for column X"* was never the right objection for any of them**,
and §10's *"Net operating assets — needs `liabilities`, absent from `_KEEP`, same rebuild as C9"*
row is wrong on both halves for the same reason. I believed the panel carried these columns too,
until I checked it rather than assuming `keep_numbers=True` meant what it sounds like.

**REASON 2 STANDS.** Altman Z and Beneish M are both inputs to `S10-ACCT`'s 2-of-3 veto and
`MA28-CARD`'s crash flag, and `S10-ACCT` was **REJECTED** on its drawdown leg.

**REASON 3 IS WEAKER THAN THE DRAFT READS, AND SAYING SO CUTS AGAINST MY OWN CONCLUSION.** It
argues O-score is *"testing the weaker of two definitions"* because Campbell-Hilscher-Szilagyi
dominates it and **CHS is batch 2's `B6`**. **`B6` was `WITHDRAWN`, not run and not rejected** —
on the draft's own instruction, because one junk arm was run and it was `B1`. So the
better-supported definition is **also untested**, and the honest form of reason 3 is *"the weaker
of two untested definitions"*, which is a reason to run CHS first rather than a reason O-score
carries no information.

**REASON 4 IS MINE AND IT IS A KNIFE EDGE, WHICH IS THE ONE HAZARD THIS RECORD TREATS AS
DISQUALIFYING.** `C9` needs four columns **at once**, so its coverage is the complete-case JOINT
rate and not the marginals. Measured on the raw export, ARQ rows from 2009:

| | `liabilities` | `assetsc` | `workingcapital` | `retearn` | **JOINT** |
|---|---|---|---|---|---|
| non-null share | 0.9998 | 0.8076 | 0.8047 | 0.9567 | **0.7673** |

**The columns go missing INDEPENDENTLY — the joint 0.7673 sits materially below the weakest
marginal 0.8047** — and by year it runs **0.734 (2014) to 0.815 (2022)**, so **the build quadrant's
own era is the WEAKEST stretch at 0.734–0.759 against a pre-committed 0.70 floor.** A kill landing
within three to six points of its own floor is the `W-28` hazard in both directions at once: the
bar may not be relaxed after watching it fail, and may not be tightened after watching it pass.
**And this is the raw export, not the tier — `O-1`'s rule means the tier's joint rate is a
DIFFERENT number and is UNMEASURED.**

**SO `C9` IS `NOT RUN`, `k` STAYS 9, and the recommendation a successor inherits is changed: run
CHS (`B6`) before O-score, because the literature already says it is the better definition and it
turns out nobody has run it either.**

### 0.2 THE `capex` SIGN — THE DRAFT'S IDENTITY REPRODUCES, AND ITS PRESCRIBED `|capex|` IS AMENDED

The draft's §1a caught a sign error in its own first version and fixed it to **`capex = fcf −
ncfo`** with Sharadar storing `capex` as a **negative outflow**. **Both halves reproduce.** On ARQ
rows from 2009 carrying all three fields (356,599 rows, count gated non-zero per `MB21`):

* the **signed** identity `capex == fcf − ncfo` holds within tolerance on **0.9998** of rows;
* `capex < 0` on **0.8462** of non-null rows.

**AND A POPULATION DIFFERENCE THAT IS NOT A DISCREPANCY, recorded so nobody tries to reconcile
them.** The draft reports `capex < 0` at **0.8874** over **381,226** rows, i.e. **all** ARQ eras;
mine reads **0.8462** over **356,599** rows **from 2009**. Two correct numbers on two populations
— the `W-28` *"two nearly-equal percentages on different objects"* shape, caught before it became
an argument.

**THE AMENDMENT: `C2`'s capex intensity MAY NOT USE `|capex|`.** The draft prescribes
**`|capex|/assets`**. Measured, that is wrong for a small but real and *economically meaningful*
slice:

* **11.29%** of non-null rows are **EXACTLY ZERO** — a firm reporting no capital expenditure,
  which is ordinary for a financial or an asset-light name rather than a defect;
* among **NONZERO** rows, **0.9540** are negative and **0.0460 are POSITIVE** — 14,542 rows over
  4,274 names — and **the signed identity holds on 0.9995 of those positive rows**, so they are
  periods in which **disposals exceeded purchases**, not sign errors.

**`abs()` scores a net divestiture as a heavy capital expenditure.** So capex intensity is
**`max(0, −capex) / assets`** — the outflow, floored at zero — with the **three states counted
separately** (outflow / exactly zero / net inflow) in the artifact. `C1`'s Δ-capex leg takes the
signed value directly and the same three-state census. **The route is declared and single:
`capex` is READ from `_KEEP`, never derived from `fcf − ncfo`** — the identity is a *check*, and
deriving it as well would be two definitions of one column (`B7`).

### 0.3 `C8` — THE STRICT-FIT REQUIREMENT BECOMES A PRE-COMMITTED KILL RATHER THAN A JUDGEMENT

The draft says *"if a register cannot implement it strictly, the arm should be dropped rather than
fitted loosely."* **A judgement made after seeing whether the loose version looks good is not a
judgement.** So it is a kill with a mechanical test: every coefficient scoring date *d* must be
estimated on rows whose date is **strictly before** *d*, pinned by a test that **fails if a
coefficient's training set contains `d` or any later date**, with a positive control that the
detector sees the violation when one is introduced. **If that test cannot be made to pass, `C8` is
`NOT RUN` and `k` stays 9.** The arm's own artifact reports, per date, the training-window end and
the scored date, so the property is checkable from the output and not only from the code.

**AND THE STRICTNESS HAS TWO HALVES, WHICH IS A CORRECTION TO MY OWN FIRST IMPLEMENTATION, MADE
BEFORE THIS REGISTER WAS COMMITTED AND THEREFORE BEFORE ANY OUTCOME.** `EG` predicts **next-year**
investment growth, so a training observation is a PAIR: predictors at `td`, realised growth at
about `td + 1 year`. My first cut paired the predictors at `td` with the growth measured AT `td` —
which fits contemporaneous growth on contemporaneous predictors, a different model whose fitted
value is not an expectation of anything.

**The second half is the one that leaks.** Requiring only `td < d` lets a pair whose **LABEL** is
dated at or after `d` into the fit: the predictors are in-sample and the outcome is from the
future. **So the kill requires BOTH dates strictly before `d`** — predictors and label — and the
artifact records the latest **LABEL** date per scored date, not the latest predictor date. A check
that looks only at where the predictors came from cannot see this, which is exactly why the
property is recorded in the output.

### 0.4 BENJAMINI-HOCHBERG WITH EIGHT ARMS AND `k` = 9

The *i*-th smallest of **EIGHT** *p*-values is compared against **i · 0.10 / 9**. **`k` stays 9
because the batch's membership was fixed in the draft before any outcome**, and shrinking the
denominator after withdrawing an arm is choosing the correction on the batch. The direction is the
conservative one: it makes every threshold harder than a `k` = 8 correction would.

### 0.5 NO FLOOR IS TYPED, AND THE THEME-IC FLOOR IS NOT AN INCREMENTAL-IC FLOOR

Both are the draft's own rules and both are adopted verbatim. Every bar is **read from
`CORRECTED_FLOORS.json`** at run time by its `key` (the artifact is a list of records carrying
`key`, `current` and `corrected`), and a test fails if any floor appears as a numeric literal in
the runner. **`max_abs_theme_ic_t`'s corrected 2.885180 is NOT written beside any incremental IC**
— `MB22`/`U2`'s rule, and `R1-VAR`'s category error.

### 0.6 A SECONDARY JUSTIFICATION OF BATCH 2's `B6` WITHDRAWAL IS NOW PARTLY MEASURABLE — AND THE WITHDRAWAL DOES NOT RE-OPEN

Batch 2 recorded that `B6`'s own kill *"would have been the binding constraint anyway"* because
its CHS inputs' coverage was **unmeasured**. One of them is now measured: **`liabilities` is
0.9998 non-null.** **That does NOT re-open `B6`**, whose primary reason was the draft's own
instruction that one junk arm be run. It is recorded because a withdrawal resting partly on an
unmeasured number should say so once the number exists.

---

## 1. WHAT EVERY ARM INHERITS — adopted from the draft's §0 verbatim

* **The incremental control is the DEPLOYED COMPOSITE**, one column from `composite_from_frame`
  (CALLED, never re-implemented), z-scored within date. All **44** build-quadrant dates survive;
  halves **24 / 20** at 2014-12-31.
* **Scored on BOTH populations, and `cap >= $10B` GOVERNS** (charter §5 Stage 1b). Wide pass +
  tier fail is **`REAL BUT NOT INVESTABLE HERE`** and does not reach Stage 2.
* **Costume kill in its own pass**, before any forward return is touched: mean per-date |ρ|
  against **each** theme, bar **0.60**. `O10`'s rule — a gating control computed in the same pass
  as the outcomes cannot be claimed to have been read first.
* **Coverage is measured on the arm's own rows, on the governing population.** `O-1` applied an
  alert-book figure to the panel and was ~17× wrong.
* **Build quadrant only**: 2009–2019 × `stable_key_half(ticker) == 0`. The check quadrant stays
  closed; no Stage-2 and no Stage-3 look.
* **"Structurally orthogonal to the incumbents" is a BANNED motivation** and no arm rests on it.
  Orthogonality is a kill input only.

## 2. THE EIGHT ARMS, AND THE KILL EACH MUST CLEAR FIRST

Every construction, every omission and every kill bar below is the draft's, unamended except where
§0 says otherwise. Ranked as the draft ranks them.

| # | arm | signal | pre-outcome kill (`K1`) |
|---|---|---|---|
| 1 | **C3** R&D-to-market | `rnd / marketcap` | **non-zero share on the tier ≥ 0.30** — a dispersion floor, not a coverage floor, because a firm with no R&D is a valid zero |
| 2 | **C4** composite equity issuance | `−[log(mcap_t/mcap_{t−5y}) − log(1+cum. total return)]` | rank ρ vs `z_neg_issuance` **< 0.95**; five-year-history share on the tier **≥ 0.70** |
| 3 | **C1** Abarbanell-Bushee, **six** signals | equal-weighted Δ-signals | six-signal computability on the tier **≥ 0.70**; |ρ| vs `quality` **< 0.60**; |ρ| vs `z_accruals_q` **< 0.60** |
| 4 | **C2** Mohanram G-score, **seven** signals | cross-sectional binaries | |ρ| vs **`z_f_score` < 0.60** — the sharpest kill in the batch |
| 5 | **C8** expected investment growth | fitted next-year investment growth | strict expanding-window fit (§0.3); |ρ| vs `z_neg_asset_growth` **< 0.60**; coverage **≥ 0.70** |
| 6 | **C5** earnings stability / persistence | AR(1) on ROA + −sd(ROA), 20 quarters | coverage at 20 quarters on the tier **≥ 0.70**; |ρ| vs `z_accruals_q` and `z_roe` each **< 0.60** |
| 7 | **C7** operating leverage | `(cor + sgna) / assets` | |ρ| vs **`z_gp_on_capital`** and **`z_op_margin`** each **< 0.60** |
| 8 | **C6** cash conversion cycle | `−(DSO + DIO − DPO)` | coverage **≥ 0.70**; **no single sector > 40%** of scoreable rows |
| — | ~~**C9** Ohlson O-score~~ | — | **NOT RUN (§0.1)**, `k` stays 9 |

**THE OMISSIONS ARE STRUCTURAL AND LABELLED ON EVERY FIGURE**, as the draft requires: `C1` is a
**six**-signal AB score (employee counts, audit opinions and LIFO/FIFO are not in Sharadar at any
dimension) and `C2` a **seven**-signal G-score (no advertising expense at any dimension).

## 3. TRIALS

**Eight equity trials**, booked in their own commit before any runner exists, re-read from
`research_log.detail()` after merging `origin/main` (`MA37` — never a session's own mid-run
figure). **The kills charge nothing**: a control can only BLOCK a finding, never produce one
(`MB1-SEL`). **`C9` charges nothing** because it is not run.

## 4. VOID CONDITIONS

1. Quoting any arm's result without its weighting named. Every figure is the **DEPLOYED** book.
2. Quoting a wide-population pass as a result when the tier fails. **The tier governs.**
3. Reading `max_abs_theme_ic_t`'s floor beside an incremental IC.
4. Typing any floor as a literal instead of reading `CORRECTED_FLOORS.json`.
5. Looking at the check quadrant, at Stage 3, or at the 1972–1998 era.
6. Relaxing a kill bar after watching it fail, or tightening one after watching it pass.
7. Re-running an arm at a different parameter after seeing its first result — that is choosing the
   parameter on the outcome (`A1`'s burn-in, batch 2's own record).
8. Running `C9`, or reading its `NOT RUN` as a finding that O-score carries no information.

## 5. WHAT THIS REGISTER DOES NOT DO

* **Nothing is adopted.** Adoption is Don's, is a vintage event, and quotes the expected return at
  **half** its backtested size (`DECISIONS.md`).
* **No public page changes** and no product copy is licensed.
* **`B4` STAYS `NOT RUN`.** The full-universe IBES cell coverage is **0.6999955119640681** against
  the inherited **0.70** and **may never be read as a pass**; the test pinning that stays. A
  **tier-level** census is a different population and is UNMEASURED — a successor may run it as a
  free pre-outcome kill, and only a tier census clearing 0.70 unblocks `B4`.
* **`B6` is not re-opened** (§0.6) and **`A1` is not re-opened** — `C3` changes the CONSTRUCTION,
  not the burn-in parameter.
* **No interaction arm.** `S7` registered four and rejected all four; `C7` is a standalone column
  by design.
