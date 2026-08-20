# CLAUDE.md — Valquo project brief (read every session)

> **FIRST: read `RUN_RULES.md` (repo root) before starting any work. It is short and
> non-negotiable — it governs pushing, handoffs, bug reporting, pre-committed thresholds, and
> never silencing a check. Every agent, every run, no exceptions.**

You are picking up **Valquo** (valquo.co), a Python/Flask stock-analysis SaaS owned by Don
(donniecorbin6@gmail.com). Be honest, concise, and never oversell. Architecture is under
**"Core file"** below (CORRECTED 2026-08-07, claims audit: this used to say "section 4 below" —
there are no numbered sections in this file and never have been, so the pointer led nowhere);
the optimization/data research roadmap is in `OPTIMIZATION_RESEARCH.md` — read it once for detail.

## What it is
Hot-stocks screener (9-theme "hot score") + options/intraday signals + a point-in-time fundamental
**backtest / Edge Lab** that proves-or-disproves the edge and tunes the screener weights. A monthly,
purely-statistical, out-of-sample-gated self-learning loop re-tunes weights.

## How to run, and the HARD RULES → **`RUN_RULES.md` PART 0**

**MOVED 2026-08-15 (master audit MA22). This file is the FINDINGS RECORD. The operating
instructions — how to run the backtest and the suites, the hard rules about `data/`, `.env`,
trades and licences, the git handoff, and the Claude-Code-vs-Cowork routing — are now PART 0 of
`RUN_RULES.md`, which is short and read first.**

Why they moved, and it is this file's own failure class: instructions buried in a 4,100-line
record rot. The removed text carried the suite count as **"62"** while the git-handoff section
at the other end of the same file said the Action *"runs all 24 suites"* — and measured on the
day of the move it was **83**. Three numbers, one file, all stale, and a reader had no way to
know which.

**Then it went to 86 before that same session ended**, because the session added three suites of
its own. A count that moves inside one sitting cannot be maintained by hand, so PART 0 **derives**
it and `tests/test_docs_entry_points.py` fails on any document that instructs from a hard-coded
one. Quoting a stale figure to record what it used to say is still fine — that is what this
paragraph is doing, and the check exempts quotations for exactly that reason.

Nothing was deleted: the four sections moved verbatim except where they were provably wrong.

## Core file: `valuation/edge/fundamental_panel.py` (the backtest engine)
- `build_fundamental_panel()` — builds the 9 themes point-in-time (reuses the live `build_frame`). `_yoy()` computes revenue/asset-growth/issuance -> `growth` + `capital_discipline`. `inst_lag_days` param stress-tests the 13F lag.
- 8 weight schemes (`_weight_schemes`), incl. `max-ir-decorr` (Sigma^-1*mu).
- Selection/validation: `walk_forward` (single-path, params) and **`cpcv_validate`** (Combinatorial Purged CV — the AUTHORITY for weights; reports PBO + Deflated Sharpe). If CPCV runs and rejects, keep defaults — do NOT fall back to walk-forward.
- `quantile_backtest` (decile / long-short), `regime_split` (edge by market-cap tier), `institutional_dependence`, `validate_institutional`.

## CURRENT STATE — the honest findings (do not oversell)
Rewritten 2026-07-30 after P5. Everything below is measured on the **full 2,710-name × 110-date
universe** (~18y, gross of costs). Several long-standing claims here were WRONG, not merely
stale — they are corrected in place and the corrections are called out, because this file is
the project's memory and the old versions had been repeated for months.

- **THE CROSS-THEME DISPERSION SORTS IN THE PUBLISHED DIRECTION AND IS A REPACKAGING OF THE
  INCUMBENTS - AND ITS ORTHOGONALITY IS GUARANTEED BY CONSTRUCTION, SO IT WAS NEVER WORTH
  ANYTHING (2026-08-20, `E-3`/`S-SEED-1`).** `PREREG_e3_theme_dispersion.md` **ACCEPTED** from
  the Frontier Scout's draft and committed **ALONE and BLIND at `5d308f5`**, markdown only, zero
  `.py`, 218 lines, a strict ancestor of every measurement commit; **1 equity trial booked at
  `fa5433a` BEFORE the runner existed, equity 238 -> 239.** **ADOPTS NOTHING, touches no book,
  ships no copy.**
  * **VERDICT `NULL`, REJECTED ON BOTH CO-PRIMARY BASES.** Incremental IC *t*: basis six
    **-0.1753** full / -0.3241 early / -0.0743 late over 69 effective dates; basis seven
    **-1.0895** / -1.0240 / -0.6799 over 49. **The largest |*t*| in any cell of either basis is
    1.0895 against the 2.71 bar**, and the arm had to clear BOTH bases (`MB18`'s rule).
  * **THE FINDING IS THE COLLAPSE RATHER THAN THE NULL. The RAW dispersion sorts in the declared
    NEGATIVE direction - median IC -0.0243 and -0.0387 at raw *t* -2.1733 and -2.3041 - and
    residualising on the incumbents removes essentially all of it.** Mean R2 on incumbents
    **0.3467 / 0.4125**, which is where `U2` measured a REPACKAGED incumbent (`gp_on_capital`
    41.3%) and nowhere near the **0.027-0.145** band four orthogonality-motivated items
    reported. The PEAD template detecting a repackaging is exactly what it is for.
  * **AND THE RAW READING CLEARS NEITHER BAR THAT GOVERNS HERE, which is the sentence that stops
    it being quoted as a near-miss: 2.17 and 2.30 pass the RETIRED 2.0 convention and fail X7's
    calibrated 2.71** - and X7 retired 2.0 because it measured **39% of PURE-NOISE draws**
    producing at least one theme at 2.0 or better.
  * **THE INTERPRETIVE CONSTRAINT THE EXECUTOR ADDED TO THE DRAFT, AND IT BINDS ANY SUCCESSOR:
    `residualise` is LINEAR and a row-wise SD is a NON-LINEAR function of the very columns it is
    residualised against, so a surviving residual here is guaranteed by construction.** A high
    R2 was therefore the PREDICTION rather than a disappointment (registered at 70/30, measured
    0.347/0.413), and a surviving incremental IC would have been a claim about **FUNCTIONAL
    FORM**, never about new information. This file already names structural orthogonality as a
    motivation nobody should run again; **this register never rested on it.**
  * **BOUNDED, NOT ABSENT, AND THE MDE TRAVELS WITH THE VERDICT.** Observed incremental effect
    **0.0211 SD against an 80%-power MDE of 0.4274** on basis six (**20.25x below**) and
    **0.1556 against 0.5071** on seven (**3.26x**). The two 80% figures reproduce `MB18`'s
    published design class **to four decimals**, an independent check that the power arithmetic
    is this record's own; and `MB18` measured the strongest RAW anchor on rows of this shape at
    **0.4346 SD**, so a NULL here means *"nothing as large as the best thing this panel has ever
    carried"*, never *"no effect"*.
  * **`B7` HONOURED BY MEASUREMENT: `composite_from_frame` is CALLED and never re-implemented,
    and C-IDENT gates on `composite(Z, w)` reproducing it elementwise at max |delta| 0.000e+00
    across 113,945 values on BOTH bases** - proved NON-VACUOUS by perturbing one cell of `Z` by
    1e-12 and requiring the identity to break, and by refusing an empty comparison rather than
    scoring it perfect (`MB21`'s C1).
  * **FOUR DEPARTURES FROM THE DRAFT THAT CHANGED THE MEASUREMENT, ALL DECLARED BEFORE RUNNING.**
    (1) **Its eligibility justification cited an unrelated measurement** - *"`C7` measured 22.01%
    of rows carrying fewer than two computable inputs"* is `MA28-CARD`'s C7 counting
    **ACCOUNTING-FLAG** inputs, not themes; the floor was kept on its own merits and the real
    cost MEASURED at **1.10% and 0.91%**, so the borrowed figure was wrong by twenty-fold.
    (2) `disp` is taken over the **PER-DATE STANDARDISED** columns, because
    `composite_from_frame` re-standardises and the raw theme spreads differ by construction
    (`S3`: `quality` near 0.50 against `insider` near 0.96) - a dispersion over raw columns is a
    sort on how many INPUTS a theme happens to have. (3) `disp` is defined **PER BASIS**, so the
    statistic and its control cover the same themes. (4) **K3 is DEGENERATE on the arm's own
    rows** - the complete-case rule makes the theme count CONSTANT there and a Spearman against
    a constant is undefined, not a pass - so all three kills are read on BOTH populations and
    fire if EITHER exceeds, and K3 is reported **STRUCTURALLY ABSENT** on the scored rows.
  * **NO KILL FIRED, AND `R6`'s GHOST DOES NOT WALK.** K1 vs `size` is the **SMALLEST** of the
    three (0.016/0.058 eligible, 0.008/0.049 on the arm), so this conviction statistic is not
    the size sort its predecessor decomposed into. K2 vs `|composite|` is the largest at
    **0.211-0.236** against a 0.60 bar - the mechanical link (`mean^2 + var = mean of squares`)
    is real and simply not large enough. **The draft called K2 the likeliest to fire at 40/60
    against firing and was right on both halves.**
  * **THE `MB7` DEFECT IS VISIBLE IN THE ARTIFACT RATHER THAN ARGUED:** basis seven records
    **`split on RAW then intersect early 14 / late 34 ok=False`** against **`EFFECTIVE 24 / 24
    ok=True`** - the exact cell `MB7` exists for. The register declared `split_used="effective"`
    beforehand, and the boundary moves **2017-07-20 -> 2020-01-22** with the required
    disclosure.
  * **EXPECTATIONS 5 RIGHT, 1 WRONG, 1 SPLIT. The miss is the draft's own expectation 4 and it
    is BACKWARDS:** it predicted dispersion's largest input correlation would be with
    `institutional` on basis seven; measured, **`institutional` is the SMALLEST at +0.008** and
    **`capital_discipline` the LARGEST at -0.198**. **And that expectation was written against a
    quantity the registered design never emits** - the three kills produce no per-theme table -
    so scoring it required a labelled post-hoc one, which is a small finding about the draft.
    The SPLIT is the sign: the RAW column is negative everywhere, while the **INCREMENTAL
    full-sample median is POSITIVE on basis six**, so *"the direction points the right way"* is
    false of the incremental statistic and may not be written.
  * **NOT DONE: no interaction arm** (§6.2, `S7`), **no weighting or sizing use** (§6.1, `S13`),
    **no `MA55` claim** (different lenses, still unrun), **no product copy** (`V3` forbids a
    per-name conviction label), and **the mechanism behind the collapse is NOT separated** -
    which incumbent carries the raw signal, and whether the residual is functional form or
    noise, would need its own register and its own trial. **21 new tests.**
    `scripts/e3_theme_dispersion.py`, `scripts/e3_addendum.py`,
    `data/free_analysis/E3_DISPERSION.json`, `E3_CONTROLS.json`, `E3_ADDENDUM.json`;
    `HANDOFF_edge_audit.md` E-3.
- **THE FLAG'S EXCESS CRASH HAZARD DECAYS MONOTONICALLY IN ALL THREE WINDOWS - 9 OF 9 STEPS
  DOWN - AND THE EXCESS CRASH *COUNT* PEAKS IN THE SECOND QUARTER, SO "FLAGS DECAY,
  THEREFORE BUY SHORT-DATED" IS THE ONE INFERENCE THIS ITEM REFUTES (2026-08-20, `E-5`/`INV-A`).**
  `PREREG_e5_hazard_curve.md` committed **ALONE and BLIND at `dd6fe93`**, markdown only, zero
  `.py`, 308 lines, a strict ancestor of every measurement commit; **1 equity trial booked at
  `5696055` BEFORE the runner existed, equity 236 -> 237**, options 305 and infra 19 untouched.
  **RE-READ AFTER MERGING (`MA37`'s rule, fourth time on this record): the live equity `N` is
  238, NOT 237** - the `E-1` lane booked a trial while this was landing, so 236 -> 237
  describes E-5's own booking and 238 is the figure to quote. The stamp was reconciled to the
  MEASURED post-merge count rather than to either side of the merge; the register is left
  UNEDITED at 237, which was correct when it was written.
  **ADOPTS NOTHING, CHANGES NO PRODUCT COPY, LICENSES NO TRADE.** The Frontier Scout's
  invention, executed by this lane, and the first consumer of `I-3`'s crash-gate library.
  * **VERDICT `UNRESOLVED` - TWO LEGS OF THREE, ON A CONJUNCTION FIXED BEFORE THE RUN.** **L1
    clears** at `HR(1)` **3.0422123745999063**, `MA28-CARD`'s own banked figure to all sixteen
    digits. **L2 clears and not narrowly.** **L3 FAILS at 0.5701 against the proposal's own 0.60
    bar, missing by 2.99pp.** Ambiguous against a pre-committed threshold is a NULL and never a
    judgement (`RUN_RULES` A6), so it is not reported as *"mostly front-loaded"*.
  * **THE RATIO PATH IS THE CLEANEST THING HERE: full 3.0422 / 2.6494 / 2.1897 / 1.8974, early
    3.4209 / 3.0680 / 2.5245 / 2.3129, late 2.9321 / 2.5315 / 2.0931 / 1.7754** - every window,
    every step down. The decay statistic reads **0.7345** full sample against a within-date
    flag-permutation p95 of **0.1932** and the null's **MAXIMUM of 0.3413 over 500 draws**, so
    the observed value exceeds every draw.
  * **AND THE TWO LEGS DISAGREE FOR A MEASURED REASON, WHICH IS THE FINDING. The excess crash
    COUNT peaks in quarter TWO - 116.8, 164.4, 125.5, 86.6 - because the KEPT base rate itself
    nearly doubles from quarter one to quarter two (0.8743% -> 1.5994%).** That is a property of
    the cumulative WINDOW, not of the flag: two quarters have more room to reach -50% than one
    does. **So the ratio falls while the excess count does not front-load, and a register with a
    single statistic would have reported whichever one it happened to pick.**
  * **FOR `O-1`'s PUT TENOR, STATED PLAINLY: NOT SUPPORTED AS A SHORT-TENOR ARGUMENT.** Quarters
    three and four together carry **~43%** of the four-quarter excess and the largest single
    quarter is the **second**. **FOR THE CARD'S COPY** the ratio is the right figure and it fades
    without vanishing - ~3.0x in the first quarter, **~1.9x in the fourth**. Quote the ratio and
    BOTH rates, never the difference (`crash_gate`'s rule, a measurement about this panel's
    era-dependent base rate).
  * **THE INSTRUMENT REPRODUCES `MA28-CARD` ON FIVE INDEPENDENT COUNTS** - 6,542 flagged rows,
    flagged share 5.7414%, full **3.0422123745999063**, early **3.4208900608295076**, late
    **2.9321220447443164** - **and the reconstructed forward return equals the panel's shipped
    `fwd_ret` at max |delta| 0.000e+00 on all 113,354 rows where both exist.**
  * **A DEFECT IN MY OWN INSTRUMENT, CAUGHT PRE-ARM BY `K3` REFUSING, AND IT IS THE REGISTER'S
    OWN §0b IN MY OWN CODE.** The first controls run failed K3 while the crash-indicator
    agreement was already a perfect **1.000000**: the gap was **591 rows whose ticker STOPS
    TRADING inside the window**, which a 63-trading-day price path cannot see, so it silently
    deleted **16 crashes, 5 of them flagged** - survivorship selection of exactly the kind §0b
    was written to forbid. **The repair is the panel's own rule RECOVERED rather than chosen:
    `fwd_ret` equals `last_close / c0 - 1` on 591 of 591 of those rows at max |delta|
    0.000e+00.** So **a DELISTED name has a TERMINAL value** - a last close is not a short
    window, it is the value of a security that ceased to exist - **while an ADMINISTRATIVE end
    of data still censors, which keeps `S22`'s and `V6-B`'s no-last-price-fallback rule intact
    exactly where it applies.** Those two censoring causes had been treated as one. After the
    repair K3 reproduces `MA28` EXACTLY rather than within tolerance. **A second defect, also
    pre-arm: the permutation null marked every shuffled cell as qualifying while the observed
    statistic pooled over cells qualifying under the REAL flag** - two different functionals,
    one of them calibrating the other.
  * **A QUALIFICATION ON MY OWN PASSING LEG, MEASURED BECAUSE IT CUTS AGAINST IT.** L2's bar is
    calibrated where the flag carries nothing (`HR` ~ 1) and the statistic is measured where
    `HR` ~ 3, and a ratio's sampling variance grows with the ratio. At a delta-method se under
    the OBSERVED rates the decay is **4.10 sigma** full sample and **3.66** late - **and only
    1.83 EARLY, whose own 80%-power MDE is 1.179 against an observed 0.760.** **So the decay is
    established on the full sample and the late half, and the early half is directionally
    consistent but is NOT independent corroboration.**
  * **THE FLAG IS TRANSIENT, AND IT IS THE NUMBER A TENOR CHOICE MOST NEEDS: only 33.5% of names
    flagged at a date are still flagged one quarter later, 27.5% at two, 23.2% at three, 22.1% at
    four.** So *"the flag's information decays"* and *"the flag goes away"* are entangled here and
    **this register does not separate them** - a name that stops being flagged is not a name whose
    risk resolved. Diagnostic, no verdict.
  * **CONTROLS. `C4`'s distress-delisting sensitivity is TIGHT and agrees** (42 events added;
    `HR(1)` 3.0422 -> 3.0384, decay -> 0.7216, share -> 0.5693, verdict UNRESOLVED). **`C3`
    REFUTES my own expectation** - flagged rows are censored by delisting at 1.93% against 1.52%,
    a ratio of **1.27x** where I registered 65/35 on 2x or more. `C6` the null is non-vacuous (500
    distinct draws, zero undefined). `C8` median market cap $2.69bn flagged against $5.19bn kept,
    reproducing `MA28` again.
  * **`K2`'s ALLOCATION PENALTY TRAVELS BEYOND THIS ITEM: 69,445 rows required at 80% power
    against 106,660 observable, where the textbook EQUAL-allocation figure is 11,640** - so
    ignoring that the flag fires on 5.74% of the panel understates the requirement **5.97x**.
    `I-3`'s `required_rows` reports both by design.
  * **REPORTED OUTSIDE THIS LANE (`RUN_RULES` rule 3): `MA28_CARD.json` was STRANDED IN ANOTHER
    WORKTREE and `I-3`'s validation could not run.** It refuses rather than passing vacuously,
    which is the correct direction; the file was in `.claude/worktrees/options-live/data/`, a
    directory that disappears with that worktree. **Copied to the primary data root and
    `i3_crash_gate_validate.py` now passes fully again - 66 leaves, max |delta| 0.000e+00, both
    routes.** Rule 9's own failure mode: the draws were stored, in a place that does not survive.
    **AND A SECOND, FIXED HERE BECAUSE IT IS ONE TOKEN:**
    `tests/test_i3_crash_gate.py`'s banked-card test resolves the data root with a helper
    and then reads the card from `REPO` instead of from the resolved root, so on ANY
    worktree it skipped even with the card present. It skipped LOUDLY, so never a vacuous
    pass - but a guard that resolves a location and then reads a different one is the
    wrong-object family. **That suite now runs 36 tests with ZERO skips**, and its own
    reproduction of `MA28`'s three window ratios independently confirms this item's `K3`.
  * **NOT DONE, named so it is not mistaken for done: `E-4` and `E-8` are NOT run**, each charges
    its own trial and needs its own blind register; **no fifth quarter, no second threshold, no
    second flag definition**; **the MECHANISM is UNMEASURED**; and **nothing here transfers to the
    BOOK** - `MB8` measured this flag firing on 3.56% of the top-decile book and catching one
    crash of eighty-four. **Expectations 7 right, 1 wrong, and discounted rather than celebrated**
    (`SC-1`'s own lesson): three were near-certainties, two were the record's default null, **and
    the binary being right hides a wrong shape - I expected L2 to be the marginal leg and L3 to
    fail clearly, and the opposite happened.** **31 new tests.**
    `scripts/e5_hazard_curve.py`, `scripts/e5_addendum.py`, `valuation/studies/hazard_curve.py`,
    `data/free_analysis/E5_HAZARD_CURVE.json`, `E5_CONTROLS.json`, `E5_ADDENDUM.json`;
    `HANDOFF_edge_audit.md` E-5.
- **DELTA-COMPOSITE IS THE CLEANEST NON-COSTUME THIS RECORD HAS EVER MEASURED AND IT PREDICTS
  NOTHING - SIX CELLS OF SIX NULL, AND THE LARGEST ONE POINTS THE WRONG WAY (2026-08-20, `E-2`).**
  `PREREG_e2_delta_composite.md` **ACCEPTED VERBATIM** from the Frontier Scout's draft and
  committed **ALONE at `c93ffc8`**, markdown only, 194 lines, a strict ancestor of every
  measurement commit, with the **equity trial BOOKED AT `441344c` BEFORE the instrument was
  written or run** (equity `N` 238 -> 239). **ADOPTS NOTHING.**
  * **THE OBJECT.** `dc(i,t) = c(i,t) - c(i,t-1)` on consecutive rebalance dates, `c` being the
    SHIPPED composite via `composite_from_frame` - Novy-Marx's fundamental-momentum hypothesis
    applied to the score itself. Verified never tested: no row among 289 in the ledger and no item
    in the 134-item audit set tests a change-in-score signal.
  * **IT CLEARS ITS COSTUME TESTS MORE CLEANLY THAN ANY CANDIDATE BEFORE IT, WHICH IS WHY THE NULL
    IS WORTH RECORDING.** `K1` vs the `momentum` theme **0.1320**; `K2` vs the banked PEAD columns
    **0.1030** max (`z_pead_car` 0.1030, `z_pead_drift` 0.0986); `K3` vs the composite **LEVEL**
    **0.4149 with ZERO of 68 dates above the 0.60 bar**. So it is not price momentum, not PEAD
    resurrected, and not a re-ranking of the product. **Five of the last six candidates were
    confirmed orthogonal and predicted nothing; this one is the cleanest of them and also predicts
    nothing.**
  * **VERDICT NULL, SIX CELLS OF SIX, declared sign POSITIVE against a 2.71 bar.** Basis six full
    *t* **-0.8501**, early **-2.6511**, late **+0.6234**; basis seven full **-0.5428**, early
    **-0.3342**, late **-0.7799**. **EVERY CELL SITS BELOW ITS OWN 80%-POWER MDE, at 0.09x to
    0.75x**, so the register's own sentence binds: a NULL means *"no trajectory effect at least as
    large as the best single signal this panel has ever carried"* (**0.4346 SD**), never "no
    effect".
  * **THE LARGEST |t| ANYWHERE IS IN THE WRONG DIRECTION AND CARRIES NO CLAIM.** Basis six's EARLY
    half at **-2.6511** misses the bar's magnitude by **0.0589** against a declared POSITIVE sign.
    It is one of six cells, contradicts the declared direction, and sits at **0.75x of its own
    detection threshold**. Reported only because a reader would otherwise discover it; **chasing it
    would be selecting a cell on its outcome and needs its own register.**
  * **AND THE DECLARED SIGN IS NOT WHAT PRODUCED THE NULL - a TWO-SIDED reading is ALSO null, for
    two independent reasons, pinned by test.** Basis six's halves **DISAGREE IN SIGN** (-2.6511
    early, +0.6234 late) so the both-halves rule fails in EITHER direction; basis seven's halves
    agree in sign and its largest |t| is **0.7799**. **The halves disagreeing in sign is this
    record's most repeated pattern - session 7's LOO, `S17`, `V6`, `S8`/`S9`, `S11`/`S12`,
    `O21-D2` - and this is a seventh instrument showing it.**
  * **`C-FIDELITY` WAS ADDED BY THE EXECUTOR BECAUSE THE DRAFT HAD NO SUCH CONTROL, and it is
    EXACT.** The composite being differenced reproduces the published record at **max |delta|
    0.000e+00** on all four figures. That hole is the one `MB18` fell into two items ago and the
    one `MA28`'s equivalent control caught **on its own first run**. A control can only BLOCK,
    never produce (`MB1-SEL`), and it moved no registered bar.
  * **`MB7`'s REPAIRED GATE DID REAL WORK, AND THIS IS THE FIRST REGISTER SAVED BY IT.** On basis
    seven the RAW-then-intersect split reads **`ok=False` at 15/33** while the EFFECTIVE split is
    **24/24** - exactly the refusal-3 case `split_used="effective"` was created for in `MB18`,
    where a refusal keyed on a property of the DATA rather than the caller's BEHAVIOUR fired
    against a register doing the right thing. **Without that repair E-2 would have been refused.**
  * **A SCOPE CORRECTION THE DRAFT DOES NOT MAKE, DECLARED BEFORE THE RUN: THE OBJECT IS A CHANGE
    IN RELATIVE STANDING.** `composite_from_frame` standardises **WITHIN each date**, so a name
    whose fundamentals improve exactly as much as the cross-section's has **`dc` near ZERO**, and a
    name standing still amid deterioration has `dc > 0`. The register's section 1 describes an
    **ABSOLUTE** improvement and the object measures a **RELATIVE** one. **Not a reason to reject** -
    a cross-sectional book ranks names against each other - but every verdict here is a verdict
    about relative standing, and that sentence ships in the artifact.
  * **THE COUNTER WAS STALE TWICE OVER**, which is why `by_domain` is re-read and never quoted: the
    draft says 235 -> 236 and equity had already moved to **238** the same day via `E-1` and `E-5`.
    **`MA37`'s rule, for the fourth time.** And a **`M1-PARSE` near-miss**: the first cut of both
    rows wrote `|t|` in prose, splitting the log row into 15 cells against a 9-column header -
    caught by `rows_malformed` before landing, and the only fix is not to put a pipe in the prose.
  * **SURVIVOR TILT PRINTED RATHER THAN ASSUMED, as section 2 requires, and it is material: median
    market cap kept $5.12bn against dropped $1.80bn, a 2.845x tilt** on 97.61% coverage over 68 of
    69 dates. **NOT DONE: no smoothing, no longer lookback, no multi-horizon delta** (section 6
    void condition 1 forbids a grid, and the consecutive-dates-only rule is pinned on a synthetic
    panel with a deliberate hole); **PEAD is not re-opened**; no product copy, no weighting change,
    no holding-period claim. **Expectations 3 right, 1 wrong, 1 split - the informative miss being
    that the draft priced a POSITIVE LATE-half effect and the strongest cell is a NEGATIVE
    EARLY-half one.** **141 suites, 0 failures; 19 new tests.** `scripts/e2_delta_composite.py`,
    `data/free_analysis/E2_KILLS.json`, `E2_ARM.json`; `HANDOFF_edge_audit.md` E-2.
- **THE GRAVEYARD AGGREGATE IS A SIZE SORT AND THE ARM NEVER RAN - `R6`'s AUTOPSY CALLED THIS
  FAILURE IN ADVANCE, ON A SET FIVE TIMES LARGER AND BUILT BY A DIFFERENT RULE (2026-08-20,
  `E-1`).** `PREREG_e1_graveyard_stouffer.md` **ACCEPTED VERBATIM** from the Frontier Scout's
  draft and committed **ALONE at `e05c33c`**, markdown only, 203 lines, a strict ancestor of every
  measurement commit, with the **equity trial BOOKED AT `dff46bc` BEFORE the instrument was
  written or run** (equity `N` 236 -> 237). **ADOPTS NOTHING** - no file under `valuation/`
  changed.
  * **THE VERDICT IS `WITHDRAWN`, NOT `NULL`, AND THE DISTINCTION IS THE WHOLE ITEM: the arm was
    never run.** `K2` - mean per-date |rho| against the `size` theme - reads **0.6114 against the
    register's 0.60 bar**, and section 4 withdraws the arm rather than scoring it. `--arm` refuses
    non-zero and a test asserts no arm artifact exists.
  * **THE KILL FIRES BY 0.0114 AND IS NOT A KNIFE EDGE, which is why the distribution was added
    as a labelled diagnostic.** Per-date |rho|: **median 0.6757, p05 0.3062, p95 0.7457, and 50 of
    69 dates (72.5%) individually above the bar.** **The registered MEAN is dragged DOWN by a left
    tail rather than up by a few dates** - the median sits 0.076 clear of the bar.
  * **THE MECHANISM, AND `R6` NAMED IT FIRST.** `K2` exists because `R6`'s autopsy found the last
    conviction aggregate decomposing into a size sort. Of the 29 graveyard signals **7 are
    `low_risk`** - the theme this file already records at **-0.352 against `size`, the strongest
    anticorrelation in the theme matrix**, with the standing note that *"low-beta/low-vol names ARE
    large caps"* - and **6 are institutional-conviction signals**, which `R6` measured at **-0.815
    to -0.854** against `size`. **Thirteen of twenty-nine come from two families already measured
    to be size proxies, and flat-weighting two proxies for one thing CONCENTRATES the exposure
    rather than diversifying it.**
  * **THE PAIR WORTH CARRYING, BECAUSE IT LOOKS CONTRADICTORY AND IS NOT: the aggregate is nearly
    ORTHOGONAL to the shipped composite (`K1` = 0.1097, passing its 0.60 bar by a mile) and
    strongly correlated with `size` (0.6114).** Both hold at once because `size` is one seventh of
    the composite's weight - and it is the sharp form of `X3`'s finding that **`size` has the WORST
    theme IC and carries the composite's ENTIRE statistical significance.** A candidate orthogonal
    to the blend while proxying its most load-bearing component is the costume that matters most.
    **The sixth structurally-orthogonal candidate in this record, and the first to die on a
    COSTUME kill rather than on a bar.**
  * **A CORRECTION TO THE DRAFT THAT RUNS AGAINST IT, DECLARED BEFORE ANY OUTCOME.** Its "expected
    ~40+" signals is wrong: **the graveyard holds 29.** And getting there required correcting my
    own first count of 16 - **the theme MEANS use far fewer columns than `NUMBER_THEME` ASSIGNS**
    (`institutional` **2 of 9**, `quality` **10 of 13**, `momentum` **3 of 5**,
    `capital_discipline` **1 of 2**), so the seven weighted themes take **24 distinct z-columns**
    and taking the registry's mapping instead would have put **17 genuinely non-incumbent signals
    in the incumbent bucket and fired `K3` spuriously.** The census is DERIVED from the theme means
    via the AST. **The direction matters: the draft set `K3`'s floor at 25 while expecting 40+, so
    the true margin is FOUR rather than the comfortable one its author assumed.**
  * **`§1` DEMANDS A "PUBLISHED SIGN RECORDED AT REGISTRATION" AND NO SUCH REGISTRY EXISTS FOR
    EQUITY SIGNALS** - `PUBLISHED_SIGNS` is options-lane machinery. Read literally the next
    sentence would exclude all 29 and fire `K3` at zero; that reading was **rejected in writing
    before the run**, for the clause's own stated reason (it exists to prevent *in-sample*
    orientation), and **the sign record was declared to be the shipped `z_` construction
    convention** - the `neg_` prefix, applied at build time in tracked source, predating the
    register, not derived from this panel's outcomes. **The arm applies no sign flip of its own**,
    pinned by test.
  * **A DEFECT IN MY OWN TEST, AND IT WAS A VOID-CONDITION BREACH.** The first mutation test proved
    the gate by flipping `all_kills_pass` to `True` and checking the refusal vanished - **which RAN
    THE WITHDRAWN ARM**, scoring the hypothesis the register had just withdrawn and writing
    `E1_ARM.json`. Caught by this suite's **own next assertion** on the following run; the file was
    **deleted UNREAD** and no figure from it was ever opened, printed or recorded. **THE PORTABLE
    LESSON: a test that proves a refusal by REMOVING it is not safe when the thing behind the
    refusal is forbidden.** Replaced by **two DISTINCT refusal messages** (missing artifact versus
    failing artifact - a hard-coded refusal cannot tell two states apart) plus an **AST check** that
    the refusal is conditional, neither of which executes the arm.
  * **THE TRIAL IS KEPT AT 237 AND THE COUNTER-ARGUMENT IS STATED.** `MB1-SEL` would license
    **zero** - it booked trials contingent on an arm that never ran and charged nothing, on the
    reasoning that a control can only BLOCK a finding. **It is kept anyway** because un-booking
    after seeing a kill fire is the shape this record warns against hardest, and **overstating `N`
    is the safe direction** (`MA6`'s call, for the same reason). Amendable if a later reader
    disagrees; the error runs the safe way.
  * **WHAT IT DOES NOT SAY: it is NOT a finding that subthreshold signals carry no aggregate
    information.** The arm never ran. `K2` is a **costume** kill - this particular flat aggregate
    cannot be told apart from a size sort. **NO COMPONENT-LEVEL CLAIM IS MADE OR REACHABLE**: no
    per-signal outcome statistic is computed anywhere in the arm path, pinned by an AST test, and
    **that prohibition would have bound identically had the arm CLEARED - clearing licenses no
    mining.** A re-open needs a materially different construction (size-neutralising the aggregate
    is the obvious one), its own register and its own trial; **it is not proposed.** The Stouffer
    secondary was **never computed on the real panel.** **Expectations: 2 right, 1 right-on-
    direction-wrong-on-margin, 2 unscorable - and the most informative miss is not on the list:
    the draft priced `K1` as the plausible kill and did not price `K2` at all. When a register
    carries several kills, the one its author does not price is worth reading twice.**
    **137 suites, 0 failures; 19 new tests.** `scripts/e1_graveyard_stouffer.py`,
    `data/free_analysis/E1_KILLS.json`; `HANDOFF_edge_audit.md` E-1.
- **THE SEASON-2 INSTRUMENTS ARE BUILT, AND ONE OF THEM DECIDES `E-6` BY A WORD: A FIVE-YEAR
  BURN-IN MEANS 60.61% OF ROWS IF IT IS TWENTY OBSERVATIONS AND 58.89% IF IT IS FIVE CALENDAR
  YEARS, WHICH LAND EITHER SIDE OF `E-6`'s OWN PRE-COMMITTED 60% KILL (2026-08-20, `I-2`+`I-3`).**
  `IDEAS_LEDGER.md` PART 3, one batch, **ZERO TRIALS, both `FIXED`-class** - no hypothesis, no
  bar, no verdict, and for `I-2` no outcome relationship computed at all. `by_domain` is
  **bit-identical** across the log append (equity **236**, options **305**, infra **19**) while
  `rows_fixed_not_counted` rises **71 -> 73**, the proof both rows were seen and correctly
  excluded. **ADOPTS NOTHING AND MOVES NO PUBLISHED CLAIM.** Nothing under `.github/` changed.
  * **THE TRIAL DIVERGENCE IS DELIBERATE AND THE COUNTER-ARGUMENT IS ON THE RECORD.**
    `IDEAS_LEDGER` prices each at 1 infra trial; both are logged at **zero** on the `MA5`
    precedent (a consolidation is a correctness repair) and the `S25`/`MB15`/`MB3` precedent (a
    census is a fact about what data exists). The scout lane's own header says its entries are
    **proposals that move no counter**, and **infra `N` gates no published claim** either way.
    The honest objection is that `I-2`'s census IS `E-6`'s pre-outcome kill input - and
    `MB1-SEL` governs: *"a control can only ever BLOCK a finding, never produce one, so it adds
    no degree of freedom to any published claim."* **No comparison to 60% is made or recorded
    anywhere in the batch.**
  * **`I-2` - THE FINDING, AND THE MECHANISM IS AN OFF-BY-ONE WORTH KEEPING.** TIDEMARK's
    expanding-percentile engine ported to **per-name** histories (expanding window; no
    look-ahead enforced by test; a burn-in returning `NaN` and never a number; publication lag
    applied). On 113,945 rows over 69 quarterly dates and 2,531 names the eligible row share runs
    **0.9335 at a 4-observation burn-in, 0.6821 at 16, 0.6061 at 20, 0.5394 at 24, 0.3160 at
    40**. **On a QUARTERLY panel the 20th observation sits NINETEEN quarters - 4.75 years - after
    the first, so twenty quarters is not five years**: requiring twenty observations AND five
    calendar years leaves **0.5889**, and twenty-one observations **0.5884**. TIDEMARK never had
    to choose because its series is dense; this panel's median name is present on 48 of 69 dates,
    so **an observation count and an elapsed span come apart and a register must say which it
    means**. `history_years` now ships on every row so a register saying "five years" can check
    whether it got five years. **`E-6` MUST DECLARE ITS READING BEFORE IT RUNS** - both shares
    are on the record, so choosing after seeing them is `MA58`'s void condition 5.
  * **THE LOAD-BEARING TEST IS PORTED AND ITS PANEL FORM IS STRONGER THAN THE SERIES FORM.**
    TIDEMARK's own comment on it is *"if this fails, every percentile in the project is a lie"*;
    the panel version must hold **for every name at once, including names that enter and leave**,
    which a single dense series never exercises. Demonstrated on the **REAL panel** rather than
    only a fixture: truncate to the first 34 of 69 dates, **52,519 rows, keys identical, max
    |delta| 0.000e+00**. **`MB24` UNTOUCHED - method crosses, no TIDEMARK data crosses**, the
    `MB22`/`MB23` fence, pinned by a path-shape sweep. **The scout's 10-year suspicion is
    CONFIRMED with a small correction: 30 eligible dates against its predicted 28, and `S18`
    needs 32**, so a decade-long burn-in does die at that floor.
  * **`I-3` - MA28's VERDICT MACHINERY IS NOW ONE IMPLEMENTATION, AND IT IS PROVED UNMOVED TWO
    WAYS.** `B7`'s nine-call-sites lesson; the consumers the ledger names are `E-4`, `E-5`
    (`INV-A`), `E-8` (`X-SEED-1`) and `O-1`'s C1. `scripts/ma28_riskcard.py` DELEGATES, and the
    library reproduces the banked `MA28_CARD.json` at **66 leaves, max |delta| 0.000e+00, zero
    moved, nothing added or removed** - and separately reproduces the **pre-refactor source
    restored from git**, which is what isolates the refactor from any data drift the first
    comparison alone cannot see. The leaf COUNT is gated, because `MB21`'s `C1` scored a perfect
    0.000e+00 on an empty frame by comparing nothing.
  * **THE DESIGN DECISION: THE ARITHMETIC MOVED AND THE BARS DID NOT.** Moving `MA28`'s constants
    into the library is the obvious approach and it is wrong - `MA5` measured that a default is
    exactly how the Harvey-Liu-Zhu bar froze at 3.0, and **these bars are worse because they are
    PRE-COMMITTED** (`MA28`'s own source: *"EVERY CONSTANT BELOW IS FROM THE REGISTER. Changing
    one after a measurement voids the item."*). A library default would let a future register
    inherit `MA28`'s pre-registration **without writing one**. So every bar is keyword-only with
    **no default**, a test asserts **no bar-shaped constant exists in the module at all**, and
    the `B2`/`B3` result keys are **FORMATTED from the bars rather than typed** - or a 3.0x
    comparison ships under a key saying 2.0x, which is `MA49`/`MA46`/`U3`'s family.
  * **`quotable()` HAS NO DIFFERENCE FIELD IN ANY STATE, AND WITHHOLDS A RATIO BUILT ON TOO FEW
    EVENTS.** `MA28-CARD`'s rule is a measurement: the base rate moved **0.3413% early against
    1.3595% late**, so the absolute gap swings **0.86pp -> 2.39pp** while the ratio barely moves
    (**3.42 -> 2.93**). The difference is still computed - `MA28`'s B1 and B3 are defined on it -
    so the library separates an internal STATISTIC from a quoted FIGURE. And `MB8`'s lesson is
    structural now: one crash of 407 is a count, not a rate, so the counts travel and the ratio
    does not.
  * **THE REQUIRED-N HOOK PRODUCES A NUMBER `E-4` NEEDS, AND IT IS NOT THE TEXTBOOK ONE.** At
    `E-4`'s own 0.87%/qtr clean-subset base rate, a 2.0x target ratio and `MA28`'s 3.56% flagged
    share, the honest requirement is **52,190 rows against the equal-allocation 5,489 - ignoring
    the allocation understates by 9.51x**, because the textbook two-proportion formula assumes
    equal group sizes and this book is nowhere near it. **So `E-4` is powered on the 113,945-row
    PANEL and is NOT powered on the 11,426-holding BOOK**, by nearly five-fold. The critical value
    is delegated to `power_gate` and still refuses to default through the extra layer.
  * **A MISSING OUTCOME IS NOT AN ABSENT CRASH - AND HERE THE GUARD IS VACUOUS, NOT PASSING.**
    `crash_flag` fails OPEN on a NaN forward return, as `MA28`'s did, and that is preserved so
    the arithmetic stays `MA28`'s; `coverage()` now reports the hole. **On this panel it is zero -
    113,945 of 113,945 rows carry an outcome - so it is reported VACUOUS rather than PASSING**
    (`O21-D2`'s `C5` precedent).
  * **FOUR OF MY OWN GUARDS FIRED AGAINST THE CORRECT TREE, AND ALL FOUR ARE ONE DEFECT.** A
    docstring citing TIDEMARK's file paths; an artifact key `fwd_ret_loaded` whose whole job is
    to record that the outcome was NOT loaded; a key
    `e6_reads_this_but_no_verdict_is_recorded_here`; and an error message containing both the
    word TIDEMARK and a colon. **Every one was a ban on a SUBSTRING tripped by prose documenting
    the rule** - `MA49`'s family, and `MB1` already wrote the fix down after hitting it three
    times in one register. **The substring ban is not a technique that works.** Replaced by exact
    match, a verdict VOCABULARY, and a path-SHAPE regex requiring a separator, **each with a
    positive control proving it still bites**. A fifth defect was found by mutation rather than by
    reading: a date test asserted that *something* raised `ValueError` and **passed with the guard
    deleted**, because pandas rejects the same string downstream - repaired by asserting the
    message and adding a case pandas accepts happily.
  * **A DEFECT OF MY OWN FROM THE PREVIOUS ITEM, FOUND HERE.** `EXPECTED_BY_DOMAIN` was assigned
    **TWICE** in `tests/test_research_log_integrity.py` - `equity: 235` above `equity: 236` - for
    four days, from `MB8`'s own merge commit `3def224`, which resolved two lanes booking trials
    concurrently by **keeping both sides**. That is right for ledger ROWS and **wrong for a
    single-valued CONSTANT**, where the first becomes dead code. The suite passed throughout
    because Python takes the last one, **which is precisely the tamper-evidence defeated**. The
    merge was CLEAN - adjacent insertions, no conflict markers, nothing to review - `MA23`'s
    cross-lane shape. Fixed, with a new guard reading the **AST** so a comment quoting an old
    stamp cannot trip it.
  * **NOT DONE, named so it is not mistaken for done: `E-6` IS NOT RUN, NOT RESOLVED AND NOT
    PRE-JUDGED**, and its 60% comparison is made nowhere in this batch; **`E-4`, `E-5`, `E-8` and
    `O-1`'s C1 are NOT run** - the library has no consumer beyond `MA28`, which is the point,
    since it was validated BEFORE anything new used it (`MB15`); **`I-1` and `I-4` are NOT
    built**; and **`IDEAS_LEDGER.md` WAS NOT EDITED** - the scout lane reserves that file and
    routes outcomes through Don, so the census wants relaying into its `OUTCOMES RELAYED`
    section. **67 new tests (30 + 36 + 1), 13 of 13 mutations caught with sources restored byte-for-byte.**
    `valuation/studies/name_percentile.py`, `crash_gate.py`, `scripts/i2_burn_in_census.py`,
    `scripts/i3_crash_gate_validate.py`, `data/free_analysis/I2_BURN_IN_CENSUS.json`,
    `I3_CRASH_GATE_VALIDATION.json`; `HANDOFF_edge_audit.md` I-2 plus I-3.
- **MA28's CRASH FLAGS ARE REAL ON THE PANEL AND NEARLY ABSENT FROM THE BOOK - AS A 0.5x SIZING
  HAIRCUT THEY REMOVE ONE CRASH IN EIGHTY-FOUR, AND RENORMALISING MAKES THE BOOK'S CRASH EXPOSURE
  SLIGHTLY WORSE (2026-08-20, `MB8`).** `PREREG_mb8_sizing_haircut.md` committed **ALONE at
  `a6d57c1`**, markdown only, 267 lines, a strict ancestor of every measurement commit, with the
  **equity trial BOOKED AT `18a4ecc` BEFORE the instrument was written or run** (equity `N` 235 ->
  236). **ADOPTS NOTHING - no file under `valuation/` changed at all**, pinned by test; adoption
  would have been **ROUTED TO DON** as a vintage event, never taken here.
  * **THE GUARD RAIL WAS CHECKED FIRST AND PASSES, so the arm dies on the crash bar and not on
    alpha.** It gives up **0.1499pp** annualised against `X7`'s calibrated **1.8629pp**
    non-inferiority margin. **KILL on the primary: the reduction is NEGATIVE - -1.44% full sample,
    -2.15% early, -1.32% late, against a 20% bar.** The 0.5x-haircut sizing family **CLOSES
    PERMANENTLY** on the register's own pre-committed terms.
  * **THE ARITHMETIC WAS DONE IN THE REGISTER BEFORE THE RUN AND IT IS WHY THE ITEM IS
    INTERPRETABLE.** A 0.5x haircut removes at most **half** the crash exposure it touches, so
    clearing 20% needs the flagged names to carry **>= 40%** of the book's crash exposure.
    `MA28`'s panel-wide figure is **19.14%**, implying ~6.1%. **In the top decile it is 1.19% - ONE
    crash of eighty-four - and the early half has ZERO flagged crashes across 34 dates**, so the
    ceiling on the reduction is **0.595%** full and **exactly zero** early. **The audit set a 20%
    bar and a fixed 0.5x haircut without multiplying them together.**
  * **THE FINDING, AND IT IS ABOUT THE BOOK RATHER THAN THE FLAG.** The `C5` census on **11,426
    top-decile holdings - the same count `S10` and `V6-B`'s C7 report independently**, which is
    what makes it the same object: **flagged 407 rows (3.56%), 1 crash, rate 0.246%;
    flaggable-and-kept 8,081 (70.72%), 52 crashes, 0.643%; UNFLAGGABLE 2,938 (25.71%), 31 crashes,
    1.055%.** The flag fires on **3.56% of the book against 5.74% of the panel**, and what it
    flags carries **1.19% of the book's crashes against 19.14% panel-wide**. **The composite's top
    decile is quality- and megacap-tilted while `MA28`'s flags fire on distressed,
    aggressively-accounted names the composite has ALREADY declined to hold** - so the overlay has
    almost nothing left to protect.
  * **AND THAT IS THE MECHANISM FOR THE NEGATIVE REDUCTION.** Renormalising to keep the book fully
    invested pushes weight off the 3.56% that is flagged and onto the 96.44% that is not - and the
    unflagged holdings carry **98.81% of the crashes**. The haircut moves capital toward the more
    crash-prone part of the book. The un-renormalised hold-cash sensitivity returns **+0.595%**,
    **exactly** the arithmetic ceiling, so it is an internal consistency check and not an
    independent result.
  * **A CORRECTION AGAINST MY OWN REGISTER, MADE BY MEASUREMENT BEFORE PUBLICATION - AND IT IS THE
    FAILURE THE REGISTER ITSELF NAMED AS THE ONE THAT MATTERS.** Section 6 priced the fail-open
    from `MA28`'s **PANEL-WIDE** figures - unflaggable rows crash at 0.8134% against the
    flaggable-and-kept 0.8928% - and called them *"marginally SAFER"* and *"a material
    mitigation"*. **IN THE BOOK THAT IS BACKWARDS: unflaggable holdings crash at 1.055% against
    0.643%, they are the MOST crash-prone bucket, and they carry 31 of the 84 crashes while taking
    NO haircut at all.** So the sizing rule is blind to a quarter of the book **and** to its
    largest crash bucket. **The register got its SIGN wrong by pricing a book-level question with
    panel-level data.** Reported **POST-HOC with NO VERDICT** (`MA28`'s own C4 precedent), and **no
    ratio is quoted on the flagged bucket - one crash is not a rate.**
  * **CONTROLS: FOUR GATING, ALL EXACT.** `C1` reproduces the published record at **max |delta|
    0.000e+00**, the control `MA28` records actually firing on its own first run (nine themes at
    1/7 gave alpha 0.0499 against 0.0717). **`C2` PROVES my decile membership IS the shipped one** -
    `quantile_backtest` does not return membership, so it is rebuilt from the same primitives and
    then required to reproduce the shipped per-date `series.alpha`: **69 of 69 dates, max |delta|
    0.000e+00**. **That control exists because `MB18` was burned by exactly this two items ago.**
    `C3` **imports** `build_flags` from `s10_accounting_veto` rather than redefining it and
    reproduces `MA28`'s flagged share **0.057414** and **6,542** rows exactly; `C4` the haircut is
    **inert at 1.0x** on both exposure and return.
  * **THE POWER STATEMENT WAS WRONG BY SIX-FOLD, IN THE HELPFUL DIRECTION, AND THE REASON IS
    PORTABLE.** The register predicted resolution near **1.87pp** - *"matched to its bar with no
    room to spare"* - by borrowing `V2G`'s measured paired HAC SE of 0.9354pp. **Measured, the
    paired SE is 0.1106pp, an 80%-power MDE of 0.314pp.** `V2G` swapped whole themes, a large and
    noisy intervention; this arm rescales 3.56% of holdings by half. **A paired difference between
    two HIGHLY CORRELATED books is measured far more precisely than one between two different
    books, so an SE may not be borrowed across perturbation sizes** - `B7`'s family, a number
    reused outside the construction it was measured on. The non-inferiority pass is therefore
    **genuinely informative** rather than the weak *"undetectable"* the register warned of.
  * **WHAT THIS DOES NOT SAY: IT DOES NOT WEAKEN `MA28`.** That register measured the flag on the
    **panel**, replicated it in both halves against its own permutation MAXIMUM and survived the
    size control that killed three sibling items. **Nothing here touches it** - the finding is that
    the flag and the book are nearly disjoint, which is a statement about the composite's
    SELECTION rather than about the flag's validity. **Nor is it evidence that the composite
    manages this risk well:** the book still suffers 84 crashes over 69 dates and the largest
    bucket of them is the one no accounting flag can even be computed for. **It closes the 0.5x
    design ONLY** - sweeping the haircut was forbidden in advance, so no other strength carries a
    verdict.
  * **A DEFECT IN MY OWN TEST, THE FIFTH INSTANCE OF ONE FAMILY.** The threshold-retyping guard
    grepped the source and **FAILED against the CORRECT tree**, because the script's own docstring
    says *"the thresholds -1.78 and 1.81 are never retyped"* - a comment documenting the rule,
    quoting the values the rule forbids. **`MA49`'s comment-versus-code defect.** Fixed by reading
    the **AST** - imports, function definitions and numeric literals - which sees code and not
    prose about code.
  * **Expectations 4 right, 2 wrong, and both misses are ONE miss:** I put 55/45 that the
    top-decile flagged share of crash exposure would EXCEED the panel-wide 19.14% (it is sixteen
    times smaller) and 70/30 that the reduction would land within 3pp of 6.12% (it is -1.44%).
    **Both follow from assuming the book looks like the panel. It does not, and that is the whole
    finding.** The audit's own prior was ~50%. **24 new tests, 9 of 9 tripwire mutations caught
    with sources restored byte-for-byte.** `scripts/mb8_sizing_haircut.py`,
    `data/free_analysis/MB8_SIZING_HAIRCUT.json`, `MB8_CONTROLS.json`;
    `HANDOFF_edge_audit.md` MB8.
- **THE IMPLIED-GROWTH EXPECTATIONS GAP IS REJECTED - AND IT IS THE FOURTH ITEM RUNNING WHOSE
  MOTIVATION WAS "STRUCTURALLY ORTHOGONAL TO THE INCUMBENTS", CONFIRMED ORTHOGONAL, AND
  PREDICTING NOTHING (2026-08-19, `MB18`).** `PREREG_mb18_expectations_gap.md` committed **ALONE
  at `1ee03ac`**, markdown only, 240 lines, a strict ancestor of every measurement commit, with
  the **equity trial BOOKED AT `be14d0c` BEFORE the instrument was written or run** (equity `N`
  234 -> 235). **ADOPTS NOTHING** - no file under `valuation/screener`, `valuation/web` or
  `valuation/engine` changed, pinned by test. The audit called it *"the cheapest genuinely-new
  equity hypothesis in this audit"* at a ~15% prior.
  * **REJECTED, AND NOT NARROWLY: the largest |*t*| in ANY cell of EITHER basis is 1.5617 against
    the 2.71 bar.** Incremental IC *t*, declared sign NEGATIVE, both halves both bases - basis six
    (69 effective dates) **full -0.6572 / early -0.6173 / late -0.4538**; basis seven (49 dates)
    **full -0.5055 / early +0.5567 / late -1.5617**. The full-sample sign is negative on both
    bases as declared, and **basis seven's halves disagree in sign.**
  * **THE NULL IS BOUNDED AND THE BOUND WAS STATED BEFORE THE RUN - which is exactly what `MB22`'s
    required-n gate was ported for.** At crit 2.71 and 80% power the design detects **0.4274 SD**
    (basis six) and **0.5071 SD** (seven), against a measured effect of **-0.0791 SD** - **5.4x
    below its own detection threshold.** For scale the strongest **RAW** anchor on exactly these
    rows is `z_fcf_margin` at **0.4346 SD** (raw *t* +3.6097). **So a NULL here means "no effect
    at least as large as the best thing this panel has ever carried", never "no effect".** The RAW
    anchors are the right control because `U2` established there is **no valid INCREMENTAL power
    control here** - every known-real signal is already an INPUT to an incumbent theme, so
    residualisation removes it by construction (confirmed: the same anchors score incremental *t*
    of +1.5509 and +0.2563).
  * **ALL THREE KILLS RAN AND NONE FIRED, AND THE COSTUME RISK WAS REAL IN DIRECTION.** `C2`
    survives at mean per-date rho vs `value` of **-0.3062** against the audit's 0.60 bar - **but
    `value` IS the largest |rho| against any of the seven incumbents** (`quality` -0.2227,
    `capital_discipline` -0.2189, everything else under 0.08), so the audit pointed the right way
    and was simply not large enough to withdraw the arm. **I registered 30/70 that it would kill
    the item.**
  * **THE LOOK-AHEAD PIN IS STRUCTURAL RATHER THAN BY INSPECTION.** `realized_growth` is FORWARD
    three-year growth - the OUTCOME - and is **never loaded at all**: the loader takes an explicit
    five-column allowlist, so the arm path cannot reference what is not in the frame, and an AST
    test asserts no attribute or subscript access anywhere names it (**the syntax tree, not a
    grep** - `MA49`'s defect, where a fixture failed against the FIXED tree because the repair
    comment quoted the defect verbatim). Mutation-tested twice, both caught.
  * **THE COLUMN-NAME TRAP IS THE SHARPEST THING HERE.** The panel already ships a column
    literally called **`gap`**, and it reproduces **`log(fair_value / price)` at max |delta|
    0.000e+00** - a **VALUATION** gap, correlating with the expectations gap at only **-0.5251**. A
    lookup by that name computes cleanly, raises nothing, and answers a different question - **and
    a much more `value`-like one, i.e. precisely the costume the arm is tested against.** Never
    loaded. `U2` pinned `term_slope_60_30` out of its arm for the same reason.
  * **THE ONE RESULT WORTH CARRYING: THE SIGN LIVES IN THE SOLVER'S BOUND, NOT IN THE
    EXPECTATIONS.** `implied_bounded` is a 3-state flag at 100% coverage - **75,034 free against
    22,283 `above` and 9,703 `below`, so 30.0% of rows hit a bound** - and the register made it a
    mandatory PARTITION rather than a pool. **Restricted to the UNBOUNDED rows the sign FLIPS
    POSITIVE on both bases (+0.2133 and +0.9267).** The verdict does not change either way, **but
    the small negative full-sample reading is carried by the bounded rows and reverses where the
    solver ran free, so it may NOT be quoted as weak support for the hypothesis** - a bounded
    `implied_growth` is a CENSORED value, and censoring correlates with extreme
    price-to-fundamentals, which is `value` again.
  * **ORTHOGONALITY IS CONFIRMED AND IS WORTH NOTHING, FOR THE FOURTH TIME.** Mean per-date R2 on
    the incumbents is **0.1392 / 0.1447**, so the gap is **~86% new information**, exactly as the
    audit argued - and it predicts nothing. **`U2`, `MA31`/`MA32`, `MA58` and now `MB18`: four
    items motivated by structural orthogonality, R2 between 0.027 and 0.145, not one clearing its
    bar.** This file already names that motivation as one nobody should run again; this is the
    fourth data point and it should settle it.
  * **TWO THINGS THE AUDIT'S ITEM DOES NOT STATE, BOTH MEASURED.** (1) `panel_s23_fairvalue.pkl`
    carries **NONE** of the seven incumbent theme columns, so the incremental-IC gate needs an
    inner join to `panel_corrected_69d.pkl` - **107,020 rows, 69 dates, 2,432 names, 98.87% of the
    S23 panel** - with `fwd_ret` from the THEME panel. (2) **`MB7`'s date defect reproduces on this
    third panel**: basis seven leaves **49 of 69 dates from 2014-01-17**, and the RAW split gives
    **14/34** against a floor of 16 while the EFFECTIVE split gives **24/24**. **Both bases were
    scored CO-PRIMARY and the arm had to clear BOTH** - taking six alone would be choosing the
    design to buy power, `MA58`'s void condition 5.
  * **A DEFECT IN `MB7`'s OWN GATE, FOUND BY BEING ITS FIRST OUTSIDE CALLER AND FIXED THE SAME
    DAY.** `require_effective_coverage` **REFUSED this register for doing the right thing**, and
    its own refusal message instructed the register to do what it had just done - because refusal
    3 keys on a property of the **DATA** rather than on the caller's **BEHAVIOUR**, so it fires
    whenever the raw split would have been unsafe, which is true of basis seven on every panel.
    Repaired with a `split_used` argument the caller must **DECLARE**, defaulting to **`"raw"`**
    so every existing caller is bit-identical and an undeclared caller is still refused;
    `"effective"` exempts refusal 3 **only**, refusal 2 still guaranteeing both effective halves
    clear the shipped floor. **`MB7`'s own 22 tests pass unchanged**, four new tests and two
    mutations pin both directions, and it **charges zero trials** - a correctness repair with no
    hypothesis and no bar.
  * **NOT DONE, named so it is not mistaken for done: `realized_growth` was NEVER SCORED, in any
    direction.** The register permits it only as an ex-post attribution computed after the verdict,
    and **that attribution was not run**; the column is not loaded at all. **`MB19` and `MB20` are
    NOT run** - each charges its own equity trial and needs its own blind register. **No claim is
    made about WHY the unbounded subset flips sign** - the censoring mechanism is a hypothesis, not
    a measurement. **Expectations 5 right, 1 wrong, 1 split** - the miss being that I put 65/35 on
    |rho| vs `value` exceeding 0.40 and it is 0.3062, so the candidate is LESS of a `value` costume
    than I expected, which makes the null slightly more interesting rather than less.
    **27 new tests, 8 of 8 tripwire mutations caught with sources restored byte-for-byte.**
    `scripts/mb18_expectations_gap.py`, `data/free_analysis/MB18_EXPECTATIONS_GAP.json`,
    `MB18_CONTROLS.json`; `HANDOFF_edge_audit.md` MB18.
- **MB1's "SELECTION CARRIES A FIFTH OF THE LOSS" IS CONFOUNDED - THE COVERED SUBSET IS SELECTED
  DIFFERENTLY IN THE TWO ARMS, AND THE CONFOUND IS TWICE THE SIZE OF THE EFFECT AND IN THE SAME
  DIRECTION (2026-08-19, `MB1-SEL`).** `PREREG_mb1sel_selection_residual.md` committed **ALONE at
  `134d8c6`**, markdown only, zero `.py`, a strict ancestor of every commit computing any new
  statistic. **ZERO TRIALS - THE ARM NEVER RAN** (`MB15`'s precedent from the same day), so options
  `N` stays **305** and `by_domain` is bit-identical (`rows_fixed_not_counted` 70 -> 71).
  **NEITHER decision is unlocked.**
  * **THE QUESTION, AND WHY IT NEEDED ITS OWN REGISTER.** `MB1` read its identity `pick_gap =
    menu_gap + selection_residual` as **TIMING ~79% / SELECTION ~21%** with a residual of
    **-1.2762pp** exceeding its own 1.00pp bar. **Every one of those is a BARE POINT ESTIMATE** -
    `MB1`'s register committed no uncertainty measure at all, and the interval it computed
    afterwards was on the **MEDIAN MENU GAP**, a different quantity. The reading was **post-hoc**.
  * **THE GATING CONTROL FIRES AND THE ARM DOES NOT RUN.** `C-RANGE` ran in **its own pass** and
    was **read before the arm** (`O10`'s process defect, not repeated), with its bar fixed in the
    register beforehand. Covered entries out-earn uncovered ones in **BOTH** arms - alert **2,446
    at +3.9830pp against 1,424 at +2.0458pp**, a shift of **+1.9372pp**; control **18,531 at
    +10.0155pp against 11,123 at +5.5330pp**, a shift of **+4.4826pp** - so the **DIFFERENTIAL is
    -2.5454pp against a bar of 1.00pp** and the arm is VOID by the register's own void condition 4.
  * **THE CONTROL IS MEASURING THE RIGHT OBJECT, VERIFIED RATHER THAN ASSUMED: its covered counts
    reproduce `MB1`'s published coverage EXACTLY** - 2,446 of 3,870 = **63.20%**, 18,531 of 29,654
    = **62.49%**.
  * **WHY THIS IS A FINDING RATHER THAN A FAILED RUN.** The residual is a **difference of
    differences**, so a coverage effect **constant across the arms cancels exactly** - that is
    `MB1`'s own robustness argument and **it is correct**. What it does not survive is a coverage
    effect that **DIFFERS** between the arms, and the control arm's is **2.3x** the alert arm's.
    **The confound is -2.5454pp; the residual it would have to explain is -1.2762pp. TWICE THE SIZE,
    SAME DIRECTION.** **So `MB1`'s selection-carries-a-fifth reading MUST NOT be quoted as evidence
    that contract selection matters.**
  * **THE MECHANISM CORROBORATES IT RATHER THAN BEING HAND-WAVED:** coverage requires a fillable
    in-band menu, i.e. a **liquid chain** - and `O10` independently measured the liquid part of this
    book at **+5.82%** expectancy against **-3.11%** for the tape-thin part. Covered ~ liquid ~
    better, on both arms; the arms simply differ in how much.
  * **AN HONEST LIMIT, STATED RATHER THAN BURIED:** the confound's path runs through `pick_gap`, and
    whether it is **fully** absorbed by the `menu_gap` subtraction is **NOT established**. So the
    correct statement is that the residual **cannot be attributed to selection**, not that it is
    **entirely** coverage. **The gate fired on a pre-committed bar and is honoured as written.**
  * **WHAT WAS FIXED BEFORE ANYTHING WAS READ, and it is the repair of `MB1`'s own failure.** **The
    MEDIAN IS BANNED BY MEASUREMENT, twice** - `O17C4` recorded the effect as *"a MEAN effect, not a
    MEDIAN one"* (+0.40pp median-vs-median against means separating 4.79pp) and `MB1` reproduced it
    on this exact object (menu medians ~**-0.50** against a **-4.7564pp** mean gap on the *same
    legs*), pinned by AST. **The verdict rule states what the interval must EXCLUDE**, in three
    mutually exclusive and all-reachable states: **CONFIRMED** needs the CI95 to exclude zero in the
    full sample **and both halves**, same sign throughout, **and the materiality bound to hold
    ACROSS THE INTERVAL** (`O21-D2`'s lesson - the nearer-to-zero end beyond 1.00pp); **REFUTED**
    needs the full-sample CI95 **entirely inside +/-1.00pp**; everything else is **UNRESOLVED**.
    **A test pins that a -1.28pp point with an interval reaching near zero - MB1's exact shape -
    does NOT confirm.** The 1.00pp bar is `MB1`'s own, **reused verbatim** rather than re-chosen
    with the estimate already published.
  * **THE GATE IS NOT VACUOUS, WHICH IS WHAT MAKES THE VOID WORTH ANYTHING.** It **PASSES** when
    both arms carry a large but **SHARED** coverage effect - the very structure that makes the
    residual robust must not trip it - fires when they are selected differently, and the arm's own
    gate is proved **no hard-coded refusal** by exercising it in isolation on a synthetic passing
    artifact, **so the gate returns while the arm itself is never run**.
  * **THE DECISION, STATED EXPLICITLY: NEITHER FIRES. `MB2` STAYS PARKED AND CONTRACT SELECTION
    STAYS OPEN** - and `MB2`'s own ledger row, landed by the concurrent audit-4 ingest, reads
    **PARKED BY DON 2026-08-19**, so it is parked by Don's decision rather than by default.** CONFIRMED would have unparked `MB2`'s grid for Don; REFUTED would have closed
    contract selection with the sound argument `MB1`'s kill could not supply. **A VOID does neither,
    and it is explicitly NOT a licence to re-run with a different statistic or a looser control
    until something clears** - a re-open needs a **materially different construction**, the obvious
    one being a coverage-matched decomposition, with its own register and its own trials.
  * **TRIALS ZERO, AND THE COUNTER-ARGUMENT IS STATED BECAUSE IT IS NOT FRIVOLOUS.** The register
    booked **3 CONTINGENT on the arm running**; it never ran. `C-RANGE` does have a pre-committed
    bar and is computed on returns, and **`O21` was corrected UPWARD for exactly that shape** - the
    distinction taken is that **a control can only ever BLOCK a finding, never produce one**, so it
    adds no degree of freedom to any published claim. If a later reader disagrees the row is there
    to amend, and that error's direction is the safe one. **129 suites, 0 failures after merging `origin/main`; 22 new tests.**
    `scripts/mb1sel_range_control.py`, `scripts/mb1sel_arm.py` (shipped complete and **never run**);
    `data/free_analysis/MB1SEL_RANGE_CONTROL.json`; `HANDOFF_optionsbot.md` 69.
- **S22's TERM-STRUCTURE CLAIM SURVIVES THE ONE NULL ITS OWN SHAPE MOST REQUIRED - AND THE
  ARTIFACT IT HAD NEVER BEEN TESTED AGAINST IS REAL, SMALL, AND APPEARS EXACTLY WHERE
  BOUDOUKH-RICHARDSON-WHITELAW SAY IT MUST (2026-08-19, `MB21`).**
  `PREREG_mb21_persistence_null.md` committed **ALONE at `ec55efe`**, markdown only, 338 lines, a
  strict ancestor of every measurement commit. **1 infra trial, infra 15 -> 16; equity `N`
  DELIBERATELY UNMOVED at 234** - re-scoring a LANDED claim on a NEW INSTRUMENT is not a new
  search, and the register said so before running rather than after. **ADOPTS NOTHING AND CHANGES
  NO PRODUCT COPY.** The audit ranked this its highest-EV item and said its most likely outcome
  was that something would come **off** the product. It does not.
  * **THE KILL WAS PRE-COMMITTED IN BOTH DIRECTIONS AND THE DECISIVE CELL WAS READ FIRST.** H=504
    `alpha_t_hac` **observed 3.830087 against a persistence-preserving p95 of 1.929708** - clears
    by **1.90 of a *t***, and the floor would have had to rise a further **1.985x** to fire. The
    observed value was **READ from the shipped `TERM_STRUCTURE.json` and pinned in the register**,
    so the target could not move once the floors were known; an AST test fails if it ever appears
    as a literal in the script. **All eight horizons clear, and SIX OF THE EIGHT clear ALL 200
    DRAWS of the corrected null** (empirical *p* <= 0.005; the other two at 1 of 200), the
    two-year observation exceeding the null's **maximum** of 3.1948 as well as its p95.
  * **THE AUDIT'S PREMISE IS CONFIRMED AND ITS MAGNITUDE IS NOT.** `S22`'s `fixed_weights_null`
    permutes **within** each date, so the placebo has no memory at all (**-0.0016 / +0.0010 /
    +0.0016** across three seeds) while the real composite's per-name rank autocorrelation is
    **0.5677** at one quarter and still **0.3983** at two years. That null WAS too easy at every
    horizon - **but only by +0.2577 of a *t* at two years, about 15% of the floor**, against a
    claim sitting 1.90 above it.
  * **THE DECOMPOSITION, REGISTERED BEFORE THE RUN AS A DIAGNOSIS AND EXPLICITLY NOT A DEFENCE,
    SPLITS ALMOST EVENLY: coverage +0.1426, memory +0.1151** at H=504. **This instrument's own
    coverage cost is comparable in size to the effect it was built to measure**, which is a real
    limitation and is stated as one rather than discovered later.
  * **THE MEMORY TERM'S SIGNATURE IS THE FINDING. BRW's artifact requires OVERLAP, and sorted by
    HAC LAG rather than by horizon it is 0 of 2 positive at lag 1 (H=63, H=126) and 6 of 6
    positive at lag 2 through 7.** A clean binary split on the exact axis the theory names. The
    direction was **named in the register before the run**, but it is scored **POST-HOC and
    carries NO verdict** - no formal test was pre-registered on it and single cells sit inside the
    sampling error of a p95 over 200 draws. **Quote the sign pattern, never a single cell.**
  * **A CORRECTION TO THE AUDIT, MEASURED: THE SHORTFALL DOES NOT GROW WITH HORIZON.** The audit
    says it *"grows with horizon - which is precisely the axis `S22`'s headline lives on"*, and
    part of the case for ranking the item first rests on that. Measured, the total effect **steps
    up once where overlap begins (+0.0972 at H=63 to +0.3778 at H=126) and is then flat or
    falling** - 0.3200, 0.2550, 0.2651, 0.2508, **0.1844 at H=441**, 0.2577 at H=504. **The
    mechanism is right and the monotonicity claim is not.**
  * **THE ONE PLACE THE CORRECTED NULL BITES IS THE LONG-SHORT LEG, AND IT COSTS A HORIZON.** It
    failed its own floor from H=315 under `S22`'s null and fails from **H=252** under this one
    (observed 1.8561 against 1.9637). **The LS floor FALLS at the two lag-1 horizons and RISES at
    every overlapping one** - the same overlap signature on a second statistic, reached
    independently. **`S22`'s standing instruction that no long-short figure may be quoted beyond
    about a year is STRENGTHENED and its boundary moves IN to a hard one year. The long-only book,
    which is the shipped product, is untouched** - `S22-DISPLAY`'s copy stands unchanged, and had
    the verdict gone the other way the register named the exact constants in
    `valuation/web/hold_horizon.py` and **routed** the edit to the app lane.
  * **`C1` IS THE STRONGEST CONTROL AVAILABLE AND IT IS EXACT: the runner IMPORTS `S22`'s own
    `arm()` and reproduces `S22`'s stored placebo draws at max |delta| 0.000e+00 across 160 of 160
    cells**, five seeds, eight horizons, four statistics. The two instruments are not merely
    comparable; the scoring path is the same object. `C2` persistence retained (real 0.5665 vs
    placebo **0.5680** at lag 1, 0.4028 vs 0.4020 at lag 8); `C3` association nil at the
    registered 200 draws (**+0.00022** and **+0.00043** against a 0.003 bar) **with a within-date
    REFERENCE arm** at -0.00021 / +0.00015, so a nonzero reading could have been attributed to the
    statistic rather than to this instrument; `C6` fixed points **1.02 of 2,474 names**, the
    theoretical expectation being exactly 1; `C8` effective coverage **PRINTED** per `MB7` and
    `RUN_RULES` PART A rule 10 (**66.4%** of rows, cross-section median **1,553 -> 976**).
  * **THE COVERAGE-PRESERVING SHORTCUT IS NOT A NULL, AND IT WAS DISQUALIFIED BEFORE THE REGISTER
    WAS WRITTEN rather than after seeing whether it flattered anything.** Permuting within exact
    presence-pattern strata keeps **96.7%** of rows against the primary's 66.4% - and leaves
    **~170 names per draw paired with THEMSELVES**, with a live residual association at H=504
    (median IC **+0.01067**, *t* **+4.106**). Pairing within a lifespan stratum pairs a name with
    one of similar era and size, and `size` is both the most persistent theme (**0.9915**) and,
    per `X3`, the carrier of the composite's entire significance. **Stratifying to protect
    coverage smuggles the signal back in.**
  * **THREE DEFECTS IN MY OWN INSTRUMENT, ALL CAUGHT BY RUNNING IT, AND THE FIRST IS THIS RECORD'S
    OWN RECURRING FAMILY.** (1) **`C1` FIRST PASSED VACUOUSLY, AT A PERFECT 0.000e+00, ON AN EMPTY
    PANEL** - the panel's `date` column is **`str`**, coercing `S22`'s stored dates to
    `pd.Timestamp` matched **ZERO of 113,945 rows**, `arm()` returned a bare status dict, and a
    max-|delta| loop that skips a `None` cell **scored perfectly by comparing nothing**. Exposed
    only because `C2` crashed on the same empty frame two controls later; `C1` now **counts the
    cells it compared and gates on the count**. **Sixth instance of the family, and the first in
    which the vacuous control was the one certifying the instrument.** (2) A read-only numpy view
    in the thinning control, caught before it could take down a two-hour run partway through.
    (3) **A DEVIATION FROM MY OWN REGISTER, CORRECTED IN THE CODE RATHER THAN IN THE REGISTER**:
    `C3` first ran on 20 draws where section 4 fixes 200, reading a knife-edge **+0.00288** against
    a 0.003 bar that the registered 200 draws showed to be noise.
  * **A CORRECTION TO THE AUDIT'S OWN PERSISTENCE FIGURES, IMMATERIAL TO THE VERDICT.** All seven
    **per-theme** values reproduce to four decimals (`size` 0.9915, `capital_discipline` 0.8882,
    `value` 0.6981, `quality` 0.6786, `momentum` 0.6414, `insider` 0.3152, `institutional`
    0.1181). The **COMPOSITE** does not: the audit's **0.5802 / 0.4099** come from a composite
    that does **not** renormalise by present-weight mass, while the **shipped**
    `composite_from_frame` - audit `B7`'s convention, and the composite `S22` actually scores -
    gives **0.5677 / 0.3983**. Diagnosed rather than asserted: an un-renormalised 0.125-weighted
    sum reproduces the audit at 0.5796 / 0.4134, and 16.3% of rows on a mid-panel date are missing
    at least one of the seven.
  * **WHAT IT DOES NOT SAY. It does not prove `S22` correct** - it shows the two-year claim
    survives the null its own shape most required, on 62 dates, on one panel. **It does not
    license the long-short leg**, which got worse. **And it does not vindicate `placebo_panel`:**
    that null really was too easy at every horizon, by roughly **+0.1 to +0.25 of a *t*** on
    overlapping long horizons, **so any future claim sitting that close to a `placebo_panel` floor
    is not safe.**
  * **NOT DONE, named so it is not mistaken for done - AND THE OBVIOUS FOLLOW-ON IS NARROWER THAN
    IT LOOKS.** `MB23` landed in another lane while this was running: it ports and VALIDATES the
    Hodrick 1992 1B estimator (6 of 6 Wei-Wright cells at max |dev| 0.0075) and cross-checks the
    **shipped H=63** statistics at a 9.18% gap inside its 10% bar. **But its own caveat binds
    here: at h=1 the windows DO NOT OVERLAP and Hodrick's sandwich carries no autocovariance term
    at all - so `MB23` validated the estimator at the ONE horizon where the overlap problem is
    absent, and `S22`'s LONG horizons are still uncross-checked on the estimator side.** The
    follow-on is therefore **not** *"run `MB23`"* but *"run the now-verified Hodrick estimator at
    H=126 through H=504 against the HAC *t*s this register scored"* - cheap, because the port
    already exists. **`S22` was NOT re-run** and `TERM_STRUCTURE.json` never written to.
    **Expectations 4 right, 1 wrong, 2 split** - the miss being monotonicity, which is the audit's
    own claim; **the audit's prior was ~55% that at least one horizon crosses and none does.**
    **126 suites, 1 ENVIRONMENTAL failure and 0 substantive after merging `origin/main`; 31 new
    tests, 6 of 6 tripwires mutation-tested with sources restored byte-for-byte.** The one
    failure is `tests/test_options_freeze.py` at `PermissionError` on a `%TEMP%` file inside
    `GzipFile`, passing **6 of 6 standalone runs** on the identical tree - **the SECOND
    independent sighting of one class the same day**, `MB16` having hit `Permission denied` on
    git objects under `%TEMP%` in `tests/test_checkout_drift.py` and measured the cause as
    sustained concurrent temp-volume I/O, **naming this item's own `--floors` shards as part of
    the load.** Suites that build real artifacts under `%TEMP%` wrap no I/O in a retry, and both
    are invisible in CI where a Linux runner has no contention - `MB42`'s shape. Reported, not
    fixed; neither suite is this lane's.
    `valuation/studies/persistence_null.py`, `scripts/mb21_persistence_null.py`,
    `data/free_analysis/MB21_PERSISTENCE_NULL.json`, `MB21_CONTROLS.json`;
    `HANDOFF_edge_audit.md` MB21.
- **QUOTE-CLASSIFIED VPIN SURVIVES ITS PRE-SCORING KILL AND THEN FAILS ALL THREE LEGS OF ITS OWN
  BAR - AND THE KILL STATISTIC THE ITEM REGISTERED IS STRUCTURALLY BLIND TO THE RENAMING IT EXISTS
  TO CATCH (2026-08-19, `MB16`).** `PREREG_mb16_vpin.md` committed **ALONE at `7fa88e5`**, markdown
  only, zero `.py`, a strict ancestor of every commit that scores an outcome; **1 options trial
  booked at `2e7bf92` BEFORE the arm ran, `N` 304 -> 305**. **ADOPTS NOTHING; `R2` stands and
  `O11` binds.**
  * **ONLY THE QUOTE-CLASSIFIED VERSION IS BUILT, AND THAT IS THE ITEM'S POINT.**
    Andersen-Bondarenko's critique of Easley-Lopez de Prado-O'Hara names its target precisely -
    the **Bulk Volume Classification** scheme, inferior to a standard tick rule, with VPIN
    predicting volatility largely because rising volatility induces systematic BVC classification
    errors. **The contested component is the classifier**, and it is the one this project already
    does properly (`O14`'s Lee-Ready, median **98.54%** of eligible prints classified). **The BVC
    classifier is built nowhere**, pinned by an AST test.
  * **THE INSTRUMENT WAS VALIDATED BEFORE THE HYPOTHESIS AND IT IS EXACT** - `MB15`'s lesson, read
    BEFORE the kill rather than after. The classifier reproduces `O14`'s banked `classified_rate`
    median **0.9854035696220825 to all sixteen digits** and its per-unit `signed_volume` at **max
    absolute deviation 0.0 across all 3,863 units**, so VPIN is built on `O14`'s instrument rather
    than on a lookalike. The arm **REFUSES** without a passing kill artifact, **mutation-tested 4
    of 4** with the artifact restored byte-for-byte.
  * **THE KILL DOES NOT FIRE: 0.0683 against a bar of 0.90** (`signed_volume` pooled **-0.0683**,
    within-month -0.0429; `unusual_volume` -0.0348, -0.0372).
  * **DEPARTURE 1, DECLARED IN THE REGISTER RATHER THAN MADE SILENTLY: the kill's "within date"
    cross-section DOES NOT EXIST on this book.** Measured: **1,570 dates, median 2 names, max 17,
    ZERO dates reaching 20, and 39.7% carrying exactly ONE name.** A within-date Spearman is
    undefined at n=1 and identically +/-1 at n=2 - a constant or noise, never a measurement.
    **`O14` hit the identical wall and sorted MONTHLY**, so the kill is taken within month with the
    pooled figure beside it and **fires if EITHER exceeds the bar**, which is stricter than either
    alone.
  * **DEPARTURE 2, AND IT IS THE FINDING: THE REGISTERED COMPARISON CANNOT DETECT THE RENAMING IT
    EXISTS TO CATCH.** VPIN is **unsigned** - mean `|buy - sell|` per equal-volume bucket - and
    `signed_volume` is **signed**. Flipping every aggressor side leaves VPIN **bit-identical** and
    **negates** `signed_volume`, both pinned by test. So correlating the two cannot see a VPIN that
    is a pure function of that feature's **magnitude**, which is precisely what the kill is for.
    **The rule was run AS WRITTEN and the defect reported rather than repaired** (`MB1`'s
    discipline). **AND HERE THE BLIND SPOT CONCEALED NOTHING**: the magnitude comparison reads
    **+0.5661**, eight times the registered statistic and still comfortably inside the bar, so
    roughly two-thirds of VPIN's rank variance is information neither `O14` feature carries. **A
    register can be wrong about what its own statistic measures and right about the answer, and
    both halves have to be said.**
  * **THE ARM IS NULL ON ALL THREE LEGS.** `O14`'s `score_arm` imported verbatim - the identical
    monthly-quintile long-short, month-block *t* and within-month permutation null `O3`/`O4`/`O5`
    were judged by. n **3,863** over **115 months**, two-sided because no sign is declarable (VPIN
    is unsigned by construction and EL O'H's own claim is about **volatility**, not direction).
    Quintile means **+0.0205, +0.0504, +0.0147, -0.0625, -0.0631**; full-sample long-short
    **+0.0835** at *t* **+1.7345** against its **own** permutation p95 of **2.0005**, CI95
    **[-0.0088, +0.1784]** straddling zero; early +0.0682 at *t* +0.9262 vs 2.0180, late +0.0992 at
    *t* +1.5943 vs 2.0498, both failing. **The halves DO agree in sign** - the one leg it passes.
  * **THE NULL CARRIES ITS OWN RESOLUTION AND THE EFFECT IS CLOSE RATHER THAN ABSENT.** From the
    arm's **own** standard error (0.04817) and its **own** calibrated bar, the **MDE is +9.64pp
    against an observed +8.35pp**, so the observed effect sits **BELOW its own detection threshold
    by 1.3pp**. **This design could not have returned a positive verdict for an effect of the size
    it actually saw.** `V6`/`S19`'s rule: quote the MDE with the verdict or do not quote the
    verdict.
  * **DIRECTION STATED WITH THE VERDICT AND CARRYING NO CLAIM:** low-VPIN alert-days earn
    **8.35pp/trade MORE** than high-VPIN ones and the two top-VPIN quintiles are the only negative
    cells - the **opposite** of a naive "informed flow is on the alert's side" story. **It is NULL,
    so no directional claim is made.**
  * **DIAGNOSTICS, NO VERDICT. The bucket count is NOT load-bearing**, which is the best evidence
    the construction is not an artefact of n=50: rank correlation against the primary **0.9493
    (n=10), 0.9800 (n=20), 0.9929 (n=100)**. **VPIN is the SECOND-STRONGEST of the six flow
    features ever measured on this book and all six are NULL** - `sweep_share` 3.0607, **VPIN
    1.7345**, `unusual_volume` 1.5107, `signed_volume` 0.6577, `block_share` 0.4366,
    `pc_flow_imbalance` 0.2556. Rho against `sweep_share` is **-0.5180**, substantial and
    **NEGATIVE** - toxic flow carries FEWER sweeps - which refutes half my own registered
    expectation.
  * **REPORTED OUTSIDE THIS ITEM (`RUN_RULES` rule 3), AND HALF OF IT IS THIS SESSION'S OWN:
    `research_log._parse` HAS NO DEDUP BY ID**, so an item that books a `PRE-REGISTERED` row and
    later appends a separate verdict row is counted **TWICE**. **`MB1` carries 2 counted rows at
    `n=2` and charged 4 options trials against a record that says 2**; **`O21-D2` carries 3 counted
    rows at `n=1` and charged 3 against a record that says 1**. **Options `N` is OVERSTATED BY 4 -
    305 reported against 301 distinct searches.** The direction is the **SAFE** one (a larger `N`
    raises every bar), which is why nothing broke and **no published claim moves**, and it is
    **deliberately NOT corrected here**: lowering `N` moves a denominator every published options
    claim is gated on in the **permissive** direction and touches another lane's rows, so it needs
    its own decision. **`MB16` books ONE row and edits its verdict cell IN PLACE**, which fixes the
    behaviour rather than the count.
  * **NOT DONE, named so it is not mistaken for done: the BVC version is NOT built and this verdict
    says nothing about it**; `O14`'s five arms are **not reopened** and stay NULL; **no incremental
    test against `|signed_volume|` was run** (a second arm is a second trial); and **nothing here
    is evidence about the ALERT ENTRY** - `R2` stands at -5.0640pp/trade against random entry, so a
    candidate would have been a candidate for a **future book that does not exist**. **ALERT DAYS
    ONLY**, and there is no pinned freeze for the tick cache so the units are pinned by a recorded
    fingerprint. **125 suites, 0 failures after merging origin/main; 26 new tests, 4 of 4 gate
    mutations refused. Expectations 3 right, 1 wrong, 1 split.** `scripts/mb16_vpin.py`, `scripts/mb16_arm.py`;
    `data/free_analysis/MB16_KILL.json`, `MB16_ARM.json`, `MB16_VPIN_UNITS.pkl`;
    `HANDOFF_optionsbot.md` 68.
- **THE VENUE-BASED RETAIL PROXY DIES BEFORE ANY ARM RUNS, ON THREE INDEPENDENT MEASUREMENTS - AND
  THE AXIS THE LITERATURE ACTUALLY USES IS SITTING UNREAD IN THE SAME CACHE (2026-08-19,
  `MB15`).** **NO ARM RAN, NO REGISTER WAS COMMITTED, ZERO TRIALS** - the item's own pre-outcome
  kill fired first, so options `N` stays **304** and `by_domain` is bit-identical across the log
  append (`rows_fixed_not_counted` 69 -> 70, the proof the row was seen and correctly excluded).
  * **THE GATE IS A TEST OF A MAPPING, AND THE MAPPING IS CHOSEN RATHER THAN GIVEN.** MB15 asks
    that *"the venue->retail mapping reproduce the published retail share (~60%) to within
    +/-15pp"*. The cache ships `exchange` as a bare `uint8` and **no legend travels with it**, so
    there is no mapping to test until somebody picks one.
  * **(1) THE IDENTIFIER IS NOT ON THIS AXIS, BY MARKET STRUCTURE RATHER THAN BY A DATA GAP.** In
    EQUITIES the standard retail identifier is the off-exchange TRF print - a venue fact. In
    OPTIONS there is **no off-exchange execution at all**; wholesaler internalisation surfaces as
    an on-exchange price-improvement auction, not as a distinct venue. Measured: ThetaData's
    published legend **does** carry off-exchange venues (**57** FINRA/NASDAQ TRF, **58** BSE TRF,
    **59** NYSE TRF) and **NOT ONE appears in 70,288,482 prints** - all 20 observed codes are lit
    options exchanges. **Their absence is informative rather than an artefact of an incomplete
    legend, which is exactly why obtaining the legend mattered**: without it, "no TRF codes seen"
    would have been indistinguishable from "the legend does not name them".
  * **(2) THE GATE IS NOT DISCRIMINATING, AND THIS IS A MEASUREMENT RATHER THAN AN OPINION.** With
    20 codes there are **2^20 = 1,048,576** retail/non-retail partitions; enumerated exhaustively,
    **633,666 - 60.4311% - land inside the registered 45-75% band**, the smallest clearing retail
    set is **5 of 20** venues, and **94.03%** of all 12-venue partitions clear. **A gate more than
    half of arbitrary mappings pass cannot fail against anyone free to choose the mapping after
    seeing the data.** Pinned with a **positive control** - a tight 59.95-60.05% band admits under
    2% - so the figure reads the band and not the arithmetic.
  * **THE AXIS THE IDENTIFIER ACTUALLY LIVES ON IS IN THIS SAME CACHE, AND NO STUDY HAS READ IT.**
    Bryzgalova-Pavlova-Sikorskaya (*J. Finance* 2023), **the source of the ~60% figure the gate is
    calibrated against**, build their proxy from an **OPRA trade CONDITION flag** - quoted from the
    paper, because my first draft used a looser search-summary formulation and dropped the date
    that turns out to matter: *"a flag for price improvement mechanisms, introduced by ... OPRA in
    **November 2019** ... trades executed through a single-leg price improvement mechanism, which
    we abbreviate as SLIM."* Not venue. Coverage is ample:
    `condition` **18 AUTO_EXECUTION 55.12%**, **125 SINGLE_LEG_AUCTION_NON_ISO 15.34%**, 126
    SINGLE_LEG_AUCTION_ISO 0.03%, 131 MULTI_LEG_AUCTION 4.95%; **`size` < 5 contracts 76.01%**,
    `size` == 1 **52.18%**; 33 distinct condition codes.
  * **(3) A THIRD DEFECT, INDEPENDENT OF BOTH, AND IT WOULD HAVE APPLIED ON THE RIGHT AXIS TOO: THE
    PERIOD IS WRONG.** The gate asks for ~60% **on the POOLED cache**; the published >60% is a
    **2020-21** figure and **the flag did not exist before November 2019**, while this cache starts
    in **2016**. A recent-period statistic is scored against a denominator spanning four years in
    which the flag **cannot fire at all**, so **even a perfectly correct proxy would have been
    measured against the wrong target.** Any successor must state its period and **cannot begin
    before November 2019**.
  * **MY OWN CENSUS INDEPENDENTLY REPRODUCES THAT DATE - the strongest verification available,
    since neither was tuned to the other.** Condition 125 by year: **absent 2016, 2017, 2018**,
    a partial-year **4.79% in 2019**, then **18.16 / 15.95 / 15.60 / 16.64 / 18.44 / 19.88%**
    through 2025 - exactly the shape of a flag switched on in November of 2019.
  * **THE UNION OF THOSE MARGINALS WAS DELIBERATELY NOT COMPUTED, AND THAT RESTRAINT IS THE POINT.**
    `single-leg auction OR (auto-execution AND size < 5)` **IS the successor register's gate**, so
    computing it here - after seeing the registered axis fail - would be choosing the design on the
    outcome. **Marginal coverage of each field is a feasibility fact; their union is the
    hypothesis.** Pinned by an AST test over the shipped scripts so it cannot be quietly relaxed.
  * **A PREMISE CORRECTION TO THE ITEM'S OWN TITLE.** It is headed *"the `exchange` field, unread
    by every prior study"*. **It has been read** - O14's `sweep_share` reads it - but **only as
    CARDINALITY** (how many distinct venues a burst touches), **never as identity**, which is the
    narrower true claim and is pinned both ways. O14's module docstring **already cites Bryzgalova
    et al. and the >60% figure**, so the reference was in the tree before this item raised it.
  * **TWO BRIEF INSTRUCTIONS COULD NOT BE FOLLOWED LITERALLY, BOTH REPORTED RATHER THAN SILENTLY
    DROPPED.** There is **NO pinned freeze for the tick cache** - `D:` holds only the two CHAIN
    freezes - so a **SHA-256 fingerprint over every unit** is recorded instead, which is the
    substance of what pinning protects. And **`pre_panel_history` is ABSENT from all 3,884 tick
    payloads**, reported **VACUOUS rather than PASSING** (O21-D2's `C5` precedent): a filter that
    never ran and a filter that ran and found nothing must not read the same.
  * **A DEFECT IN MY OWN GUARD, THE FOURTH IN THIS FAMILY IN TWO SESSIONS.** The test pinning
    *"`sweep_share` reads venue only as cardinality"* banned the substring `retail` and **FAILED
    AGAINST THE CORRECT TREE**, because O14's own docstring discusses retail flow - the
    comment-versus-code family after `MB1`'s three substring bans and `MA5`'s source sweep. It now
    strips comments and string literals with `tokenize`, and **the stripper itself is pinned
    non-vacuous in both directions** (it must keep `def sweep_share` and drop `retail`), because a
    stripper returning `""` would make the guard pass by seeing nothing.
  * **SCOPE, STATED IN EVERY OUTPUT: alert-days only.** The cache is exactly the alert days, so
    every figure here is conditioned on them and **none generalises to the tape**. 3,884 units,
    186 symbols, 1,574 dates, **70,288,482 prints**.
  * **NOT DONE, named so it is not mistaken for done: THE REGISTERED ARMS ARE UNTESTED, NOT
    REJECTED**, and **the successor is NOT registered here** - an item on the condition+size axis
    needs its own blind pre-registration, its own trials and its own session, with the
    range-restriction control in a separate pass (`O10`'s process defect, which the item itself
    names). **`MB1`'s selection follow-up is not folded in.** **19 tests, 7 of 7 mutations caught
    with sources restored byte-for-byte.** `scripts/mb15_venue_census.py`,
    `mb15_gate_satisfiability.py`, `mb15_condition_census.py`;
    `data/free_analysis/MB15_VENUE_CENSUS.json`, `MB15_GATE_SATISFIABILITY.json`,
    `MB15_CONDITION_CENSUS.json`; `HANDOFF_optionsbot.md` 67.
- **`O11`'s RUIN RESULT IS THE NON-EARNINGS HALF OF THE BOOK - THE EARNINGS-SPANNING HALF ENDS
  ABOVE ITS START AT $5,000, NOT THE $250,000 THE AUDIT EXPECTED (2026-08-19, `MB3`).**
  **ZERO TRIALS** - a computation on banked distributions with no hypothesis and no bar of its own
  (the `S25` / `X7RECON` / `MB31` class), so equity stays **234**, options **305**, infra **17**.
  **ADOPTS NOTHING AND LICENSES NO TRADE.**
  * **THE QUESTION AND ITS KILL CONDITION WERE THE AUDIT'S, QUOTED VERBATIM BEFORE THE RUN:**
    *"at what account equity does the cap-10 ruin arithmetic permit an earnings-spanning book to
    end above where it started?"*, closing the family permanently above **$250,000** and becoming
    a live design need below it. **MEASURED: $5,000**, bracketed between $2,500 and $5,000, a
    **single** break-even crossing - so the pre-committed `UNRESOLVED` branch (more than one
    crossing) did not fire. **The audit's own ~85% prior that this closes is REFUTED.**
  * **THE CONTROL IS THE FINDING.** At $50,000 and cap 10 the **spanning** half ends at
    **$130,855** and the **not-spanning** complement at **$24,391**, with `O11`'s recorded
    whole-book **$37,059** sitting between them. **So `O11`'s headline - a +3.27%/trade
    positive-expectancy book ending BELOW its start - is driven by the trades that do NOT span an
    earnings announcement.** The halves are not required to sum: 388 `UNKNOWN` rows are dropped
    from both.
  * **THE PARTITION REPRODUCES `O17C4` EXACTLY, which is what makes it the same object** - 1,987
    spanning against its recorded `n_spans` of 1,987, 1,495 not, 388 UNKNOWN **dropped and
    counted** rather than folded either way (29 of 186 names are foreign private issuers with no
    earnings dates). Nothing is reimplemented: the shipped `simulate_book` under the shipped
    `MAX_CONCURRENT`, and the shipped `owns_the_event`.
  * **A DEFECT IN THE AUDIT'S MECHANISM, FOUND BY RUNNING IT.** It reasons that harvesting a
    thin-tail mean needs many small positions *"which is exactly the configuration `O11` measured
    to end below its starting equity"*. **The low-end failures are AFFORDABILITY, not ruin**: at
    $1,000 only **2 of 1,987** trades are taken because the account cannot afford the premium.
    The book does not go broke at small size - it never gets on.
  * **TWO CAVEATS THAT MUST TRAVEL WITH IT. (a) This is the ALERT book's spanning subset**, and
    `O17C4` measured alert-spanning **LOSING** to random-spanning (+8.42% against +10.30%, *z*
    **-4.4726**), so the tradeable form is *"buy calls spanning earnings"* **with no alert in it**
    and that book was **NOT** simulated. **(b) `O11` GOVERNS** - below the bar means a live design
    need requiring its own blind register, **which is not proposed**. The effect is a **MEAN** one:
    DTE-matched median-vs-median is **+0.40pp**, so the typical trade is a near-total loss either
    way. The control's own resolution is **UNRESOLVED** by the same rule (two crossings, off a thin
    71-trade cell) and is reported as a **direction**, not a figure.
    `scripts/mb3_event_ownership_equity.py`, `data/free_analysis/MB3_EVENT_EQUITY.json`;
    `HANDOFF_edge_audit.md` MB3.
- **EVERY "MINIMUM DETECTABLE EFFECT" THIS PROJECT HAS EVER PUBLISHED IS A 50%-POWER FIGURE,
  NOT AN 80%-POWER ONE - AND THE HODRICK CROSS-CHECK VALIDATES THE H=63 STATISTICS WHILE BEING
  STRUCTURALLY UNABLE TO CORROBORATE THEM (2026-08-19, `MB22`+`MB23`).**
  `PREREG_mb22_mb23_power_and_hodrick.md` committed **ALONE at `9dee135`**, markdown only, a
  strict ancestor of every measurement commit. **Both items are INFRA: `N` 15 -> 17, equity
  untouched at 234, and infra `N` gates no published claim. ADOPTS NOTHING, MOVES NO CLAIM** -
  both branches of `MB23`'s bar were pre-committed to move nothing. **Options is untouched BY
  THIS ITEM and reads 305, not the 304 measured mid-session** - a concurrent lane booked a trial
  while this was landing, and the stamp in `tests/test_research_log_integrity.py` was reconciled
  to the MEASURED post-merge count rather than to either side of the merge conflict. Taking one
  side would have mis-stamped a domain neither lane had wrong. The register is left unedited at
  304, which was correct when it was written; **`MA37`'s rule, for the third time: RE-READ
  `by_domain` after merging and never quote a session's own mid-run figure.**
  * **`MB22` - THE VOCABULARY CORRECTION, AND IT APPLIES TO THREE FIGURES ALREADY IN THIS FILE.**
    `S19`'s **+0.020549**, `V2G`'s **1.8708pp** and `V6`'s **+4.177pp** are all `crit x se` - the
    effect at which the **POINT ESTIMATE** would just reach the bar, which is detected **half the
    time**. The 80%-power MDE is `(crit + 0.84) x se`, **1.42x larger at `crit` 2.0**, so those
    become +0.029180, 2.6565pp and 5.9313pp. **Neither number is wrong as stated; quoting one as
    the other is.** All three reproduce from the ported function without being told the answer,
    which is what proves it measures the quantity Valquo already means.
  * **THE STRONGEST CONTROL IS VALQUO'S OWN, NOT TIDEMARK'S. `V2G` published 1.8708pp as what its
    design "resolves" and then separately computed its power against a true 1.95pp gap as
    55.0%** - and `power_at(1.95, se 0.9354, crit 1.96)` returns **55.0%** by a different route.
    A design whose detection threshold sits just below the effect it tests has about a coin flip
    of seeing it. That is exactly what a 50%-power threshold means, and `V2G` had both halves of
    it on the page without the two being connected.
  * **THE EXTERNAL CONTROLS REPRODUCE TIDEMARK'S PRINTED ARITHMETIC EXACTLY** - the charter power
    table at `crit` 1.96 (IR 0.20 -> 196, 0.30 -> 87, 0.15 -> 348), `hlz_hurdle(66)` 2.8947,
    155.0 required years at IR 0.30, and the four IR-needed figures 0.41 / 0.55 / 0.74 / 0.52.
    **`hlz_hurdle` is IMPORTED and never re-derived (`MA5`), and `critical_value` REFUSES to
    default** - a default is precisely how the HLZ bar froze at the constant 3.0.
  * **NO CHECK SHIPS, AND THE REFUSAL IS THE POINT (`MB30`, with `MA21` binding).** ~68 historical
    registers state no MDE in this form, so a corpus sweep would fire on essentially all of them
    and be switched off inside a week - the identical shape `MA21` already declined when a
    blank-verdict warning would have fired on 41 legitimate ledger rows. **`RUN_RULES` PART A
    rule 11 binds future registers instead**, and the library makes obeying it one line.
  * **`MB23` - VERDICT `VALIDATED`, AND THE MARGIN AND THE MECHANISM BOTH TRAVEL WITH IT.**
    Long-short Newey-West **2.6199** against Hodrick **2.8604**, gap **9.18%**; top-decile alpha
    **4.3762** against **4.6719**, gap **6.76%**; bar 10%, required on both. **THE LONG-SHORT CELL
    CLEARS BY 0.82 OF A PERCENTAGE POINT - a 9% bar would have failed it.**
  * **AND `VALIDATED` MEANS LESS THAN IT SOUNDS, WHICH IS THE HONEST PART. At `h = 1` the horizon
    EQUALS the rebalance interval, the windows do not overlap, and Hodrick's sandwich carries NO
    autocovariance term at all** - so it **structurally cannot see** the lag-1 autocorrelation
    Newey-West corrects for (**0.189** long-short, **0.081** alpha). The two agree because that
    correction is small here, **not because two independent methods converged**, and the Hodrick
    *t* lands nearer the **NAIVE** *t* (2.8361, 4.5174) than the HAC one in both cases. **This
    validates the ported instrument. It does NOT independently corroborate the HAC number.**
  * **THE ESTIMATOR IS VERIFIED AGAINST PRINTED NUMBERS, NEVER AGAINST MY OWN EXPECTATION** -
    Wei-Wright (2009) FEDS 2009-27 Table 1, **6 of 6 coverage cells at `alpha` = 0 at max abs
    deviation 0.0075** against a pre-registered 0.03, **plus the more discriminating half, the
    PUBLISHED COLLAPSE away from the null** (0.700 against a printed 0.71 at `alpha` 0.05, 0.495
    against 0.53 at 0.10). An estimator merely returning ~0.95 everywhere passes the null test
    and fails that one. **The reason for that standard is on the record: TIDEMARK's own first
    implementation summed the regressors while keeping the h-period residual and returned
    *t* ~ 0.3 at every horizon against a bootstrap p ~ 0.018** - it looked like "no evidence" and
    was believed. **The defect is reconstructed and pinned**, so a future session reintroducing it
    goes red.
  * **`POWER_GATE` 5.2's SPECIFICATION ERROR IS REPRODUCED INDEPENDENTLY ON THIS IMPLEMENTATION**:
    on the verified cell the estimator is correctly sized (Var(*t*) **1.012**, rejection **0.040**
    against a nominal 0.05) and the criterion **as committed** there - q97.5 of |*t*| within 10%
    of 1.96 - **FAILS on it**, because 1.96 is the 97.5th percentile of the **SIGNED** *t* and the
    right figure is ~2.24. **A rule that flags a known-good case is broken**, so the rejection
    rate ships as the decision rule and the misspecified quantile is carried beside it, marked.
  * **THE H-SWEEP IS A DIAGNOSTIC AND CARRIES NO VERDICT, by a void condition fixed in advance.**
    The gap widens to **17.4%** (long-short) and **31.5%** (alpha) by `h = 8` - `S22`'s territory -
    and **`MB21` is NOT run here**, so re-scoring `S22` against a better standard error while
    leaving its null mis-specified would change one half of a comparison. The sweep also cumulates
    the same 69 quarterly draws rather than rebuilding `S22`'s per-horizon panel columns, so it is
    a **related object, not `S22`'s own construction**. **Quoting any `h > 1` cell as a verdict
    about `S22` voids the register.**
  * **A DEFECT IN MY OWN INSTRUMENT, AND IT IS `MB22`'s SUBJECT COMMITTED INSIDE `MB23`'s TESTS.**
    The criterion test first ran at 250 draws, where its own +/-0.015 tolerance is **1.1
    Monte-Carlo standard errors wide** - so it asserted something its sample could not resolve,
    and a correctly-sized estimator failed it. Fixed by deriving the draw count (1,200, 2.4 se),
    **not** by loosening the criterion, which would have been silencing the check. **Two further
    guards of mine fired on their own docstrings** - the comment-versus-code family for the sixth
    time - and now read the **AST**. **37 tests, 8 of 8 mutations caught across both modules with
    sources restored byte-for-byte.** `valuation/edge/power_gate.py`, `valuation/edge/hodrick.py`,
    `scripts/mb22_mb23_power_and_hodrick.py`, `data/free_analysis/MB22_MB23.json`;
    `HANDOFF_edge_audit.md` MB22+MB23.
- **THE ALTERNATIVES MENU IS SCORED AND THE KILL FIRES - AND THE CLOSURE IT ANNOUNCES IS NOT
  SOUND, REFUTED ON THREE MEASUREMENTS OF THE SAME DATA (2026-08-19, `MB1`).**
  `PREREG_mb1_alternatives_menu.md` committed **ALONE at `33ad7ee`**, markdown only, a strict
  ancestor of every measurement commit; **2 options trials booked at `476650e` BEFORE the run,
  `N` 300 -> 302**, exactly the counter the audit item specifies. **RE-READ AFTER MERGING, per
  this file's own repeated rule: the live options `N` is 304, NOT 302** - a concurrent lane landed
  `MB7`, `MB31` and `MB32` the same day and charged 2 further options trials. 300 -> 302 describes
  MB1's own booking; 304 is the figure to quote. Read only from the **pinned**
  harvest freeze. **ADOPTS NOTHING; `O11` binds and nothing here licenses a trade.**
  * **THE REGISTERED VERDICT: the pooled menu MEDIAN gaps are -0.7310pp early and -0.5366pp late,
    both inside the 1.00pp bar, so the kill FIRES on the weaker half as written** (`any`, never
    `all`, pinned by an AST test) and the arms pass records `CLOSED - contract selection is
    IRRELEVANT`.
  * **AND THAT CLOSURE IS NOT SOUND. (1) THE REGISTERED STATISTIC IS STRUCTURALLY BLIND.** Both
    arms' menu medians sit at about **-0.50** - the typical menu leg is a near-total loss on BOTH
    books - so the median is pinned in that dense loss mass where it cannot see the right tail an
    option book's expectancy is built from. **`O17C4` had ALREADY measured this on this book**,
    recording the effect as *"a MEAN effect, not a MEDIAN one"*. **The register chose the one
    statistic this project had already shown cannot detect what is being tested.**
  * **(2) A PAIRED CLUSTER BOOTSTRAP DOES NOT RESOLVE THE RULE IN ANY WINDOW.** The register
    commits **no uncertainty measure at all** and closes a question permanently on a bare point
    estimate. On R3's own name-year cell, same keys drawn for both arms: **CI95 [-13.8011,
    +15.7701] early, [-1.2154, +0.0922] late, [-7.0143, +0.1521] full - the early interval spans
    29.6pp around a -0.73pp estimate.** The clustering is pinned **by measurement**: on correlated
    legs it must widen the interval more than threefold or the diagnostic measures nothing.
  * **(3) THE DECOMPOSITION THE ITEM EXISTS TO PRODUCE CONTRADICTS THE VERDICT.** Re-derived on
    **exactly** the covered entries rather than differenced against R2's whole-book figure:
    `pick_gap = menu_gap + selection_residual` reads **-6.0326pp = -4.7564pp DAY (78.8%) +
    -1.2762pp SELECTION (21.2%)**, same sign both halves (-1.7223pp early, -1.1450pp late).
    **Selection carries about a fifth of the loss and its residual EXCEEDS the 1.00pp bar the
    register itself set for materiality.** The instrument exposure is bounded rather than
    hand-waved - the residual is a **difference of differences**, so a bias constant across the
    arms cancels exactly, pinned by test.
  * **(4) THE KILL CONDITION'S INFERENCE IS INVERTED RELATIVE TO THE ITEM'S OWN LOGIC.** Under
    that identity, menus that **coincide** mean the day effect is nil and therefore the ENTIRE
    loss is selection - so a small menu gap implies selection carries **everything**, not nothing.
    **The rule was registered VERBATIM from the audit because the brief required it, and running
    it verbatim is precisely what surfaced that it does not follow.** **THE BEST AVAILABLE ANSWER
    is TIMING ~79% and SELECTION ~21% on the covered subset - not a closure, and this row must NOT
    be read as having closed contract selection.**
  * **THREE GATING CONTROLS IN THEIR OWN PASS, `--arms` refusing without a passing artifact.**
    **C1 the menu contains the shipped pick on 2,446 of 2,446 covered entries AND the menu's own
    argmin IS that pick at 1.0000** - what makes this the engine's menu rather than a
    reconstruction; **C2** coverage parity **0.7134pp** against 2.0pp; **C7, a control the register
    did not anticipate** - the control books store **no** `underlying_entry`, so BOTH arms derive
    it from `raw_close` and it reproduces the alert book's stored value **EXACTLY on 2,446 of
    2,446** at median relative error 0.000e+00. **Composition is ruled out by measurement**: mean
    menu depth **6.816** against **6.771**.
  * **A PREMISE CORRECTION FIXED BEFORE ANY OUTCOME: the audit's "median 636 alternatives per
    entry" is the WHOLE CHAIN, and the engine's own in-band fillable menu has a median of FIVE** -
    864 raw -> 432 calls -> 31 DTE -> 10 moneyness -> 9 solvable delta -> **5 fillable**, the
    fillability filter alone removing nearly half (low volume 53.5%, wide spread 44.1%). **`MA31`'s
    warning, far more severe than the item anticipated** - it predicted the direction, not the
    magnitude - so **any reading leaning on a distribution over ~636 is void**. The arms still pool
    **16,672** and **123,415** legs.
  * **DEFECTS IN MY OWN INSTRUMENT, all caught before any result.** The half boundary was taken
    over alert **LEGS** where the register says the covered **ALERT SET** - a four-year error on
    the pin's own fixture, driven by one deep-chain entry - and taking it over the covered set also
    fixes it BEFORE any leg is scored. **The raw legs were not persisted** (rule 9), so the
    interval would have cost a second 75-minute pass; caught 3 minutes in and restarted, and the
    dump now precedes all summarising. **That fix then carried its own defect** - the test harness
    did not redirect the new path, so the suite wrote into the REAL `data/` dir and would have
    clobbered the artifact rule 9 exists to protect. **And my own no-verdict test was wrong three
    times, each by banning a SUBSTRING**, flagging in turn a docstring disclaiming the kill, a key
    named `pass` that labels which pass wrote a file, and a local naming which side of the bar an
    interval reaches; it now reads the AST and separates label from decision by **value type**.
  * **COVERAGE 63.20% and 62.49%; the uncovered remainder is UNMEASURED and never read as zero.**
    **121 suites, 0 failures after merging `origin/main`; 36 new tests across three suites.**
    `scripts/mb1_alternatives_menu.py`, `mb1_interval.py`, `mb1_decomposition.py`;
    `data/free_analysis/MB1_CONTROLS.json`, `MB1_MENU.json`, `MB1_INTERVAL.json`,
    `MB1_DECOMPOSITION.json`; `HANDOFF_optionsbot.md` 66.
  * **`MB42` LANDED ALONGSIDE, `FIXED`-class and ZERO trials** (`by_domain` bit-identical,
    `rows_fixed_not_counted` 65 -> 66). A gate suite was **GREEN in CI and RED on the only machine
    holding the data it guards**: a path-separator literal behind a mount guard that returns early
    when the D: drive is absent, so on Linux the assertion **never executed**. **A CORRECTION TO
    THE AUDIT'S OWN PRESCRIBED FIX, measured on both platform implementations:**
    `normcase(normpath(x))` is **EQUAL under `ntpath` and DIFFERS under `posixpath`**, because a
    backslash is an ordinary filename character on POSIX - invisible while the test skips, but
    **MB42's own kill condition requires a fixture making the comparison RUN on both, and at that
    point the prescribed fix breaks the test it was meant to repair.** Shipped a separator- and
    case-insensitive comparison plus both fixtures. **The durable part is MB42's own framing, the
    `MA5`/`MA23` family restated: a guard whose only real execution is skipped is the defect, and
    the separator is merely how it surfaced.**
  * **REPORTED OUTSIDE THIS LANE (`RUN_RULES` rule 3): `VALQUO_MASTER_AUDIT_4.md` is tracked with
    its PDF and items JSON and carries 42 `MB` items, and NONE had a ledger row before this
    session** - a grep for any `MB` id returned nothing, so every audit-4 item read as never
    raised. The `MA` precedent is one row per item ingested as its own verified batch, which is
    where `MA18`'s severity mismatch was caught. **That ingest has not happened and is NOT done
    here.**
- **O21's DEFERRED ARM IS RESOLVED AT LAST, AND THE DIFFERENCE DOES NOT SEPARATE FROM ZERO -
  THE WHOLE 95% INTERVAL SITS INSIDE THE BAR (2026-08-18, `O21-D2`).**
  `PREREG_o21d2_alternative_contract_pnl.md` committed **ALONE at `1d23ee1`**, markdown only, a
  strict ancestor of every measurement commit; **trial booked at `f86ebba` BEFORE the run, options
  `N` 297 -> 298**, equity untouched at 232. **ADOPTS NOTHING, CHANGES NO LEDGER VERDICT, AND DOES
  NOT RE-OPEN `O21`** - it replaces the string `NOT COMPUTABLE` with a measurement and nothing
  else in that row moves. **The ONLY same-hypothesis re-open the blind re-open list (`10977a2`)
  authorized.**
  * **THE REFERENT NOW EXISTS, AND THAT IS WHY THIS WAS ANSWERABLE RATHER THAN SETTLED.** `O21`
    could COUNT the 179 of 3,870 entries (4.63%) at which a dividend-corrected pricer picks a
    different contract and could NOT PRICE them, because the trade-scope freeze holds a full chain
    only on **ENTRY** dates - median **2** chain dates for an alternative. The pinned harvest
    freeze `D:\thetadata\freeze_rawpull_2026-08-18` holds a full chain on **EVERY session**
    (AAPL-2018: 251 sessions, median 1,558 contracts, bid and ask 100% non-null).
  * **VERDICT IMMATERIAL, AND THE BOUND SAID SO BEFORE THE RUN.** Implied BOOK expectancy effect
    across all 179 is **-0.1653pp** against `O21`'s **own** 1.00pp bar reused verbatim. The
    register fixed the arithmetic first: **a 4.63% divergence share needs a 21.62pp mean per-trade
    difference to move book expectancy by 1.00pp**, so a 3.6pp per-trade figure reads as large
    only until you see it is 0.17pp of the book. **Quote the bound with the verdict or do not
    quote the verdict.**
  * **NEITHER STATISTIC SEPARATES FROM ZERO, AND THIS IS A CORRECTION AGAINST MY OWN FIRST
    DRAFT, MADE BEFORE PUBLICATION RATHER THAN AFTER.** That draft was headed *"it trades tail for
    typicality"* and told a mechanism story: the alternative sits at a **lower strike on 93.9%** of
    entries at a median absolute delta gap of **0.129** above a 0.35 target, so it is deeper ITM
    and **LESS levered**, which should fail totally less often (**higher median**) while giving up
    the right tail this book's expectancy is built from (**lower mean**). **The point estimates
    have exactly that shape - mean -3.57pp, median +0.67pp - and then neither survives a test.**
    The mean reads *t* **-0.8045** with **CI95 [-12.28, +5.13] pp**, straddling zero; the median rests on
    the alternative winning **61 of 113** pairs, two-sided binomial **p 0.4519**, a coin flip.
    **So the shape is CONSISTENT WITH that mechanism and is NOT EVIDENCE FOR IT** - a story fitted
    to two estimates that do not separate from zero is a story, and this record's own repeated
    lesson is that such stories survive by being repeated. **No directional or mechanism claim is
    made.**
  * **AND THE VERDICT GETS STRONGER RATHER THAN WEAKER, WHICH IS THE POINT OF TESTING IT.** A
    bound has to hold across the **INTERVAL**, not merely at the point estimate. **At the CI95's
    most adverse end the implied book effect is -0.5681 pp and at the other end +0.2374 pp, so the
    ENTIRE 95% interval sits inside the +/-1.00pp bar.** That is a far more robust `IMMATERIAL`
    than a point estimate, and it is what makes the door genuinely closed rather than closed at
    one number.
  * **NO DIRECTIONAL CLAIM IS MADE, BY THE REGISTER'S OWN RULE.** The halves DISAGREE - early
    **-10.59pp** (n 56), late **+3.32pp** (n 57) - so the pre-committed rule forbids
    *"the corrected pricer picks worse contracts"* **in either direction**, and **E2 is recorded
    UNRESOLVED even though its full-sample sign was right.** The register predicted this and said
    why in advance: n = 113 split in two is thin and the halves are unbalanced by a coverage tilt
    registered before any outcome.
  * **C2, THE NULL INSTRUMENT, IS PERFECT - AND IT IS THE STRONGEST INSTRUMENT RESULT THIS LANE
    HAS PRODUCED.** **2,309 non-divergent entries re-simulated on the harvest reproduce the banked
    `return_pct` on 2,309 of 2,309 - reproduction 1.0000, ZERO differing, ZERO unusable.** Those
    entries hold the SAME contract in both arms, so it checks that the two instruments agree where
    they cannot legitimately disagree. **The register named a genuine risk in advance - the
    harvest carries MORE holding days than the trade-scope freeze, so a stop could fire on a day
    the banked simulation never saw - and it did not materialise on a single trade.** `C1`
    reproduces `O21`'s selection **exactly** at 3,870 of 3,870 with 179 changed, so these are
    literally `O21`'s 179. Both gating controls ran in **their own pass** and `--arms` **refuses**
    without a passing artifact.
  * **INSTRUMENT AGREEMENT WAS ESTABLISHED BEFORE THE ARM, NOT INFERRED FROM IT:** the harvest and
    the trade-scope freeze match on **bid AND ask exactly, 115 of 115** banked contracts at entry.
    That is what licenses pricing **BOTH** arms on one instrument, the base being **RE-SIMULATED**
    rather than read from the banked book, so a difference is attributable to the contract and not
    to the data source. The exit engine is the **SHIPPED** `simulate_trade`, unmodified.
  * **COVERAGE IS 113 of 179 = 63.1% AND SYSTEMATIC RATHER THAN RANDOM, FIXED BEFORE ANY
    OUTCOME:** 2016-2018 at 100 / 100 / 94.7% because Tier A ran to completion, 2019-2025 at 31.2
    to 70.0% because Tier B was cancelled at 490 of 961 units once the census showed those years
    were not perishable - so **the covered set is EARLY-TILTED**. **The 66 uncoverable entries are
    UNMEASURED and are never read as zero.**
  * **THREE DEFECTS IN MY OWN INSTRUMENT, ALL CAUGHT BY RUNNING IT.** (1) A **literal `%` in prose
    about a percentage** inside a `%`-formatted note string was read as a conversion and crashed
    the artifact write - **AFTER every statistic had been computed and printed, so no number was
    affected**, but the first run produced a verdict with nothing on disk to support it. Repaired
    by removing `%`-formatting from prose about percentages **rather than escaping it**, and the
    re-run reproduces every figure to the digit. (2) **My first coverage probe used the wrong
    window** - it required harvest units only to the EXIT date and returned 115 (64.2%), when
    `simulate_trade` holds to **EXPIRY** whenever no trigger fires and **12.3% of alternatives
    carry a different expiry**; corrected to **113 (63.1%)**, recorded in the register rather than
    quietly replaced, and the looser figure is used nowhere. **(3) THE WORST OF THE THREE, because
    it would have made the other two unverifiable: MY TEST SUITE WOULD HAVE PASSED VACUOUSLY under
    this project's own runner.** `RUN_RULES` line 25 runs each suite as its own process and judges
    by **exit code**; a file with no `__main__` block defines its tests, **executes nothing and
    exits 0**, so all 21 would have counted as a passing suite while testing nothing. Found by
    running the documented runner instead of `pytest tests/` — **which is NOT this project's test
    command and, run in one process, produced ~10 failures that were artefacts of the runner** —
    and censused afterwards rather than assumed: **113 of 113 suites carry the block and mine was
    the only exception.**
  * **A NULL HERE IS NOT A FINDING THAT THE PRICER IS CORRECT.** It is a finding that the pricer's
    contract-selection error is too small a share of the book to matter, measured on 63.1% of the
    affected entries. **The pricer is still deliberately NOT changed**, and had the result been
    material the consequence would have been a **NEW** register proposing a change, not an edit to
    `O21`. `C5` `pre_panel_history` is reported **VACUOUS rather than PASSING** - the key is
    ABSENT on all 114 units read. **Expectations 4 right, 0 wrong, 1 unresolved**, discounted
    rather than celebrated because the priors came from measured facts already in the record.
    **21 tests, 3 of 3 tripwires mutation-tested with sources restored byte-for-byte.**
    `scripts/o21d2_alternative_pnl.py`, `data/free_analysis/O21D2_CONTROLS.json`,
    `O21D2_ALT_PNL.json`; `HANDOFF_optionsbot.md` 65.
- **RETURN SEASONALITY IS UNINTERPRETABLE HERE, AND THE FINDING IS ABOUT THE INCREMENTAL-IC
  TEMPLATE RATHER THAN ABOUT SEASONALITY: RESIDUALISING ON THE SEVEN INCUMBENTS SILENTLY MAKES
  ANY SUCH REGISTER A POST-2014 TEST ON 49 OF 69 DATES (2026-08-18, `MA58`).**
  `PREREG_ma58_return_seasonality.md` committed **ALONE at `6f998fc`**, markdown only, a strict
  ancestor of every measurement commit; **budget booked at `eb85ca7` BEFORE the run**. **Equity
  `N` 232 -> 234.** **ADOPTS NOTHING** - no file under `valuation/` changed, `NUMBER_THEME` still
  has 53 entries, so `MA58`'s own tripwire stays green and **is correct to**.
  * **THE VERDICT IS `UNINTERPRETABLE` ON THE REGISTER'S OWN PRE-COMMITTED POWER RULE**: on the
    rows the arms are measured on **BOTH power controls fail** - `z_gp_on_capital` raw IC *t*
    **1.1363** and `z_ret_6_1` **1.3493** against a 2.0 bar. **BOTH READINGS AGREE, WHICH IS
    REPORTED BECAUSE IT CUTS THE OTHER WAY: the arm would ALSO have been REJECTED on its own
    bars** - incremental IC *t* **+2.1607** full, **+0.6705** early, **+2.1438** late, failing
    X7's 2.71 in all three windows. **The power rule conceals no pass; what it buys is the correct
    label - "not measurable here", never "absent".**
  * **THE PORTABLE FINDING, AND IT IS INHERITED BY EVERY ITEM USING THE PEAD/U2 TEMPLATE:
    complete-case residualisation on the seven weighted incumbents restricts the panel to 49 of
    69 DATES.** Cause measured and single: **`institutional` has 71.7% coverage and its FIRST date
    with 20 or more names is 2014-01-17.** Drop it and all 69 return. **So an incremental-IC gate
    on this panel is a post-2014 test unless it says otherwise, and the "early half" it reports is
    not the early half it thinks it is** - here that cell holds **14 dates**, below even `S18`'s
    16-date floor. `U2`, `MA31` and `MA32` all ran this template and none reported it.
  * **NEITHER RESTRICTION ALONE WOULD HAVE FAILED THE BAR - THEY COMPOUND.** `z_gp_on_capital`
    across four nested populations: full panel **+3.6739**, plus the seasonality depth filter
    **+2.2125**, full plus complete-case **+2.1934 on 49 dates**, both **+1.1359**. `MA31`/`MA32`'s
    three-population result reproduced on a different restriction - **and the +3.6739 against their
    independently measured +3.6745 is what proves both instruments sound**, as does every theme
    reproducing this file's own corrected-panel table to four decimals.
  * **THE LEDGER ROW'S OWN DEPTH PREDICTION IS REFUTED, IN THE DIRECTION THAT HELPED.** It expected
    depth to bind at the panel's EARLY end and to force a covered-subsample on the `S18`/`U2`
    protocol. Measured: **all 69 dates are covered at every depth tried, never below 1,161 names**,
    so no subsample protocol was invoked and a **full both-halves gate was available** - and the
    shortfall is at the **LATE** end (**81.6%** eligible on the first date against **66.3%** on the
    last). The panel grows 1,471 -> 1,842 names and the names it grows by are young. **A
    price-history requirement on this panel is a RECENT-IPO screen, not an early-period screen.**
  * **THE PUBLISHED PATTERN POINTS THE RIGHT WAY AND IS NOWHERE QUANTITATIVELY.** The annual-lag
    arm is positive in the declared direction and the non-annual arm sits on zero (**+0.0377**
    full), which is Heston-Sadka's shape - but the paired contrast fails its own permutation p95 in
    **all three windows** (+0.02367, *t* +1.2440 against p95 +1.5508). **A pattern that points the
    right way and cannot be separated from noise is not a replication.**
  * **THE ONE NOTABLE NUMBER IS ORTHOGONALITY: mean R2 on the incumbents is 0.0755**, so the signal
    is ~92% new information, and it is **not a repackaged theme** (largest theme correlation
    `value` **-0.1511**; `momentum` only **+0.0699**, refuting my own prediction that the k=1 window
    would make it a momentum proxy). **Real new information that predicts nothing measurable here** -
    `U2`'s dissociation on a price-only signal.
  * **C-DEPTH IS WHY THE "FIX THE LAG STRUCTURE FIRST" CONSTRAINT EXISTS, AND IT EARNED ITS KEEP.**
    At **K=5 the pattern REVERSES** - `seas` +0.7790 against `nonseas` **+2.1655**, which clears its
    own full-sample p95. **A depth sweep could have told either story and the two contradict.**
    K=10 was fixed on availability before any result; K=5 ran once and carries no verdict.
  * **TWO DEFECTS IN MY OWN INSTRUMENT, BOTH CAUGHT BY GUARDS WRITTEN TO CATCH THEM.** (1)
    **`_tstat`'s shipped `sd > 0` guard is value AND LENGTH dependent** - `[0.1]x3` returns *t*
    **1.019e16** while `[0.1]x4` returns exactly **0.0** - found by my own mutation test, fixed with
    a relative floor and **PROVED INERT at 299 shared leaves, ZERO moved**. **The shipped `theme_ic`
    carries the identical hazard and is deliberately NOT changed** (`U2`'s reason: repairing it in
    this lane would decouple the statistic from the bar calibrated on it) - **still open, edge
    lane's.** (2) **My own vacuity companion was VACUOUS**: it tampered a window's INTERIOR, and a
    window return is `close(end)/close(start)-1`, so it is **path-independent by construction** -
    `MA28`'s Altman-Z lesson in a third costume.
  * **NOT DONE, named so it is not mistaken for done: the register was NOT amended after the
    controls ran**, `institutional` was **NOT** dropped to recover the 20 dates (that is choosing the
    design to buy power, void condition 5), **K was NOT re-swept**, and **no LEVEL statistic was
    computed for the verdict** (the `P1S0-CONTROL` clause - all three legs ask SORTING questions,
    pinned by an AST test). **A re-open is NOT a re-run of this design**: the binding constraint is
    the template's complete-case rule, and changing it changes what every incremental-IC item
    measures, so it needs its own register and its own trials. **Expectations 3 right, 3 wrong, 1
    split. 115 suites, 0 failures after merging `origin/main` - the one pre-merge failure was NOT this item's (`MA18`'s ledger row carried 9 cells against a 10-column header, already repaired on main at `1b50f0b`); 19 new tests, 4 of 4 tripwires mutation-tested.**
    `scripts/ma58_seasonality.py`, `data/free_analysis/MA58_SEASONALITY.json`,
    `MA58_CONTROLS.json`; `HANDOFF_edge_audit.md` MA58.
- **THE FRONTIER'S `rf + 43 bps` FINANCING EDGE IS A MID-PRICE ARTEFACT - AT EXECUTABLE PRICES IT
  IS `rf + 342`, AND A DEEP-ITM CALL IS CHEAPER THAN EXACTLY ONE OF THREE MARGIN CARDS, THE MOST
  EXPENSIVE ONE (2026-08-17, `DEEPITM-FIN` + `V5-REREAD`).**
  `PREREG_v5reread_deepitm_financing.md` committed **ALONE at `9ffe05a`** - one `.md`, 279 lines,
  zero `.py`. **ADOPTS NOTHING, RECOMMENDS NOTHING.** Options `N` **294 -> 297**; equity untouched
  by this item. Read from the **freeze**; the mutable `data/options` store was never opened.
  * **`V5` WAS ALREADY DONE AND IS NOT RE-RUN - ZERO TRIALS.** It landed **2026-08-09**
    (`scripts/slippage_report.py`, `PREREG_v5_slippage.md`, 57 tests) and re-reads **unchanged at
    3 entry fills and ZERO exit fills**, so the pre-registered headline M3 has **n = 0** against a
    floor of 30 and the verdict stays **INSUFFICIENT** - what its own section 6 predicted at
    90/10. **A NAVIGATION HAZARD THAT CAUSED THE RE-BRIEF: V5's ledger row is in
    `VALQUO_EXTENSIONS.md` line 14 and NOT in `VALQUO_LEDGER.md`**, so a ledger grep returns
    nothing and the item reads as never done.
  * **THE BRIEF'S PREMISE IS REFUTED BY THE DATES AND ITS BAR IS A CATEGORY ERROR.** The three
    fills are stamped **2026-08-04, 2026-08-07, 2026-08-07** and session 14 is **2026-08-09**, so
    all three PREDATE it and **zero have accrued since**. And *"the modelled 33.4bps"* is audit
    **B11's EQUITY cost in bps of STOCK NOTIONAL** against a book that pays bps of **PREMIUM** -
    a **~12x** category error `slippage_report.py` already prints on every run, keeping the
    constant only as `EQUITY_ONE_WAY_BPS_NOT_APPLICABLE`. Its real bar is **410.0 bps of premium**.
    Re-registering would have been **two definitions of one bar**, the B7 defect class.
  * **THE REFRESH PATH IS BROKEN, AND IT NEEDS DON RATHER THAN CODE.** The weekly `track-backup`
    Action **FAILED 2026-08-16** (run `31932667751`, 3s): *"the job was not started because recent
    account payments have failed or your spending limit needs to be increased."* Last success
    **2026-08-09**. **No fresher read of the live book exists on any surface this lane can reach.**
    **Re-open condition: V5 becomes answerable at `n >= 30` CLOSED legs** - M3 needs exits.
  * **THE FINDING IS THE PRICE CONVENTION, AND IT CORRECTS THE FRONTIER RATHER THAN REFUTING IT.**
    On 12,904 matched call/put pairs (185 names, 2016-01-19 -> 2025-10-15, both legs passing the
    shared `usable_quote` rule, 60-90 DTE, delta 0.85-0.95 with delta solved on the **PUT** leg):
    at **MID** the excess reads **+66.94 bps** pooled and **+42.81 bps on non-payers - an
    independent corroboration of the frontier's +43** on a different universe, source and code.
    **At EXECUTABLE prices - buy the call at the ask, sell the put at the bid - it is +342.35 bps,
    5.1x larger.** The frontier said mids were *"a lower bound on the embedded rate"* and was
    right; **a COST question has to be answered at the prices an account pays.**
  * **THE ROLL IS HALF THE COST AND IT CANNOT BE AVOIDED.** All-in **701.87 bps/yr** = financing
    342.35 + **roll spread 340.06** + commission 3.57, at median **DTE 73 and 5.0 rolls/yr**
    (589.92 after O18's rho 0.6743, an **EXTRAPOLATION** here since rho was measured on 35-delta
    60-DTE contracts). **The financing benefit REQUIRES rolling** - exercising means paying the
    strike in cash, which defeats the purpose - **so 60-90 DTE, the SHORTEST tenor, is the worst
    case**, which is precisely what the frontier's own *"only clearly positive at a tenor we do
    not own"* implied.
  * **THE ANSWER: Robinhood Gold `rf + 420` MORE EXPENSIVE, Robinhood standard `rf + 995`
    CHEAPER, IBKR Pro `rf + 150` MORE EXPENSIVE.** The brief expected *"cheaper than margin, with
    caveats"* and **as stated that is wrong.** The registered prior predicted this and **all four
    of its cells were right.** Margin rates are **ASSUMPTIONS** - published retail cards, not
    anything measured here - and every output says so.
  * **TWO POST-HOC CUTS, BOTH LABELLED, AND THE FIRST REFUTES MY OWN REASON FOR RUNNING IT.** By
    rate era the option route is **more expensive than Gold in ALL FIVE eras**, its own cost stable
    at **616-754 bps** while the Gold spread swings **52-567** - so the answer is **NOT**
    era-dependent as I expected. Restricting to non-payers gives **578.2 bps** and the same two
    answers. **C3 IS UNRESOLVED AND SAID TO BE:** payers read **+109.27 bps** at mids against
    non-payers' +42.81, **2.5x and in the OPPOSITE direction to the bias the frontier warned
    about** - either a real clientele effect or residual PV(D) mis-specification.
  * **COVERAGE LIMITS THE QUESTION AND WAS FIXED BEFORE ANY NUMBER: 11 of 86 Valquo Index names
    are in the freeze (12.8%).** So *"is it cheaper for INDEX names"* is **not answerable on owned
    data**; the Index cell (482 pairs) carries **no verdict** and quoting an Index-scope claim from
    the 185-name universe is a **void condition**. **`U6`'s blocker in a new place.** 46 of 185
    names sit below the n = 30 floor and are **listed rather than pooled**.
  * **A DEFECT IN MY OWN INSTRUMENT - AND IT IS THE GUARD I WROTE LAST SESSION, REPEATED.**
    `_data()` resolved paths with `os.path.exists`, and the worktree carries an **EMPTY**
    `data/bulk/prepared/bars` while the primary holds **502** files, so the empty directory
    shadowed the populated one and the first run reported **`spot series: 0`** and zero surviving
    pairs. **EXISTENCE IS NOT POPULATION** - exactly what `optionable_universe.is_populated_cache`
    exists for. **The second fix matters more: zero pairs now RAISES.** It had flowed downstream
    and merely happened to crash on a missing column; with one more column present it would have
    produced a clean, plausible **coverage null** from an input that never loaded - **`MA31`'s
    failure mode**, which did not raise either time.
  * **GATING CONTROLS MUTATION-TESTED:** `--arms` **refuses** without a passing controls artifact,
    proved by flipping `all_gating_pass` false, watching it exit **2**, and restoring the artifact
    **byte-for-byte**. **It is a COST measurement and says nothing about returns** - `P1S0` closed
    the options-expression family on the return side and **this does not reopen it**.
    `data/free_analysis/DEEPITM_FIN.json`, `DEEPITM_FIN_CONTROLS.json`;
    `HANDOFF_optionsbot.md` 63.
- **P1S0's DEAD EARLY HALF WAS A WEAK PERIOD *AND* A WEAKER UNIVERSE AT ONCE - THE QUESTION'S
  OWN DICHOTOMY IS FALSE, WHICH IS WHY THE PRE-COMMITTED RULE RETURNED NULL (2026-08-16,
  `P1S0-CONTROL`).** `PREREG_p1s0control_period_or_universe.md` committed **ALONE at `dc618c4`**,
  markdown only, a strict ancestor of every measurement commit; budget booked at **`be4bd36`
  BEFORE the run**. **Equity `N` 231 -> 232.** **NOT A RE-RUN OF `P1S0`** - no arm, placebo or
  verdict of it recomputed, `P1S0_GATE.json` never written to, every optionable figure READ from
  it, pinned by four AST tests and mutation-tested. **THE OPTIONS-EXPRESSION FAMILY STAYS `CLOSED`
  and this register could not move it.**
  * **THE QUESTION.** `P1S0` closed the family on a both-halves failure whose early half - 2016 to
    2020 on the optionable universe - is not weak but **absent** (cum alpha **-0.00082** at H=252;
    HAC *t* **0.8352** at the power anchor against its own floor of 1.6974) while the full sample
    **passes** at +14.045%/yr, *t* 3.3731. Was 2016-2020 weak because those are **optionable
    names**, or because it is a weak **period**? Measured by scoring the **FULL equity panel** over
    `P1S0`'s own dates and halves, same construction, as a control.
  * **THE CONSTRUCTION IS VERIFIED, NOT ASSERTED: the full-panel `full` cells reproduce `P1S0`'s
    shipped `reference_full_panel_same_dates` BIT-FOR-BIT at all three horizons** -
    0.02378082572517831, 0.09391044377802256, 0.1311161852362568, seventeen significant figures, on
    identical date counts. Same object, same dates, same code. **And the gap that made a new item
    necessary: that block ships the FULL SAMPLE ONLY - the early/late split of the full panel on
    those dates had never been computed, and that split is the entire question.**
  * **VERDICT NULL. Leg 1 FAILS** - full-panel early `alpha_t_hac` **1.2536** at H=63 against its
    **OWN** full-panel `early_p95` of **1.9308** - **while leg 2 is POSITIVE**, H=252 early cum
    alpha **+0.060427**. The legs disagree, and ambiguous against a pre-committed rule is a NULL
    (`RUN_RULES` A6), never a judgement call.
  * **THE FINDING IS THAT IT IS BOTH, AND THEY INTERACT.** **(1) The PERIOD is weak for the full
    panel and not marginally: over 2016-2020 the full 2,531-name panel DOES NOT SORT** -
    monotonicity is **POSITIVE at all three horizons (+0.115 / +0.152 / +0.248, deciles running
    BACKWARDS)** and the long-short *t* is **negative at all three (-0.078 / -0.846 / -2.424)**,
    against a late window at mono -0.915 / -0.830 / -0.818 and ls *t* +2.07 / +1.50 / +2.04.
    **(2) AND the optionable subset is WEAKER STILL in that same window** - the full panel beats it
    by **+1.467pp (H=63), +6.124pp (H=252), +1.527pp (H=504)** annualised, every horizon the same
    direction. **(3) AND IT REVERSES LATE**, where optionable is **BETTER** by -9.704pp, -10.927pp
    and -1.555pp. **So the optionable subset is not uniformly worse: it is worse early and better
    late** - a period effect and a universe effect interacting, which is exactly the shape a
    two-branch rule cannot express.
  * **THIS CORROBORATES `R1`'s OWN FRAGILITY WORK RATHER THAN CONTRADICTING `R1`'s HEADLINE.** `R1`
    found a ~10-year window centred on 2009-2019 at alpha **+1.66% (*t* 1.39)** with **8 of 70**
    rolling windows not significant; `X4` found the investable margin **not demonstrable since
    2014**. 2016-2020 sits inside both. ***"The headline passes every subperiod"* is true of `R1`'s
    coarse halves and thirds and is NOT a claim about this specific five-year window.**
  * **WHAT IT MEANS FOR THE GATE, AND IT IS A FINDING ABOUT THE GATE AND NOT A LICENCE.** `P1S0`'s
    early-half failure **cannot be cleanly attributed to optionable names**, because the full panel
    also fails to sort over the same window - **and it cannot be dismissed as pure period either**,
    because the optionable subset is measurably worse at every horizon in exactly that window.
    **The honest statement is that `P1S0`'s early half was measuring a weak PERIOD and a weaker
    UNIVERSE at once, and its gate cannot separate them.** The family stays CLOSED; a reopen would
    need its own register, its own trials and its own blind commitment, and **is not proposed.**
  * **A DEFECT IN MY OWN REGISTER, AND IT IS WHY THE ITEM RETURNED NULL: LEG 2 ASKED A *LEVEL*
    QUESTION WHEN THE ITEM IS ABOUT *SORTING*.** *"Is the top decile's cumulative alpha positive?"*
    cannot distinguish *"the composite works here"* from *"the composite does not rank, but the top
    decile drifted up with the market"* - and the full panel's early window is exactly the second
    case, cum alpha **+0.0604** while monotonicity is **+0.152** and the long-short *t* is
    **-0.846**. **Had leg 2 been a SORTING statistic both legs would have agreed and the rule would
    have resolved PERIOD.** I picked the wrong second statistic before seeing any number, and the
    NULL is the register working as intended - refusing to resolve rather than letting me choose
    the reading afterwards. **THE RULE WAS NOT RESTATED AFTERWARDS.**
  * **THE FLOOR EXTRAPOLATION THE REGISTER FORBADE WAS REAL, NOT DECORATIVE.** Void condition 3
    forbade comparing a full-panel statistic with `P1S0`'s restricted-universe floors. Measured:
    the **full-panel** `early_p95` is **1.9308** against `P1S0`'s restricted **1.6974** at H=63 -
    **0.23 of a *t* HIGHER**, so borrowing it would have been **permissive**. The verdict is
    unchanged either way (1.2536 fails both), but 619 names is not 2,531 and the guard earned its
    keep.
  * **NOT DONE, named so it is not mistaken for done: `P1S0` was NOT re-run, the family was NOT
    reopened, no third leg was added, and H=504 was NOT promoted** from diagnostic to decisive -
    though it is the one early cell with a *t* above 2 (**+2.1791**), it has no floor, carries no
    verdict, and promoting it after seeing it is what the register forbids. **No claim is made
    about WHY 2016-2020 is weak** - that mechanism is unmeasured and would be its own item.
    **109 suites, 0 failures; 14 new tests, 3 of 3 tripwires mutation-tested.**
    `scripts/p1s0_control_period_or_universe.py`, `data/free_analysis/P1S0_CONTROL.json`;
    `HANDOFF_edge_audit.md` P1S0-CONTROL.
- **THE ACCOUNTING RED-FLAG RISK CARD CLEARS ITS PRE-COMMITTED GATE - AND THE CONTROL THAT WAS
  SUPPOSED TO KILL IT PASSED 5 OF 5 WITH THE EFFECT STRONGEST IN MEGACAPS (2026-08-16,
  `MA28-CARD`).** The first post-audit research item, and the ONE register resolving `MA26-A` +
  `MA28` + `MA54-1` - three audit ids, one hypothesis.
  `PREREG_ma28_accounting_riskcard.md` committed **ALONE at `6ff578b`**, one `.md`, zero `.py`, a
  strict ancestor of every measurement commit; **trial budget booked at `7f294df` BEFORE the run**.
  **Equity `N` 230 -> 231**; options 294, infra 15. `BACKTEST_RESULTS.json` needs no re-run - the
  HLZ hurdle moves 3.2979022 -> 3.2992174, 0.0013 of a *t*, and per `MA21` the artifact may
  legitimately LAG the log.
  * **THE GATE WAS THE CRASH-RATE REPLICATION AND NOT ALPHA, ENFORCED IN CODE RATHER THAN
    PROMISED.** `top_decile_alpha` is computed **nowhere in the arm path** - pinned by an AST test
    that reads the syntax tree rather than grepping, because the script's own docstring says the
    words. `S10-ACCT` already ran this as a screen and was REJECTED on the portfolio-drawdown leg,
    and `S10` had measured *why* that leg can never pass: this book's max drawdown is **one
    market-wide quarter, COVID 2020Q1 at trough index 44 of 69**, which no name-level flag can move.
  * **THE RESULT. Names flagged by 2 or more of Beneish M > -1.78, Altman Z < 1.81 and top-decile
    within-date external financing lost more than half their value over the next 63 trading days at
    2.6597% against 0.8743% - ratio 3.0422x - and IT REPLICATES:** early half **3.4209x** (mean
    per-date difference +0.8593pp, NW *t* 2.7780), late half **2.9321x** (+2.3932pp, NW *t*
    4.5788). **Every window's observed value exceeds the permutation MAXIMUM of 500 draws, not
    merely the p95** (empirical *p* < 0.002 each). Coverage read first: Beneish 68.59%, Altman
    76.67%, ext-fin 94.51%; flagged share **5.7414%, 6,542 rows, reproducing `S10-ACCT`'s count
    exactly**, which is what proves it is the same object.
  * **C4 WAS THE CONTROL THE REGISTER PREDICTED WOULD KILL IT, AND IT DID THE OPPOSITE - THIS IS
    THE FINDING.** Altman Z contains market cap directly (`X4 = marketcap / liabilities`), so the
    flag is **mechanically** size-linked, and `U7`, `S10` and `V6-B` were each decided by exactly
    that failure mode. Flagged names **are** smaller (median cap $2.69bn vs $5.19bn, 0.52x) - but
    the effect does not weaken within size, **it strengthens monotonically: 2.010x in the smallest
    quintile to 5.169x in megacaps**, 5 of 5 clearing.
  * **THE MECHANISM IS IN THE DENOMINATOR, and it is the most portable thing here.** Across
    quintiles the KEPT rate falls **14.5x** (2.554% -> 0.176%) while the FLAGGED rate falls only
    **5.6x** (5.133% -> 0.910%). **Large companies almost never halve in a quarter - unless their
    accounts are stressed, in which case they still do at nearly 1% a quarter.** So the flag carries
    most information exactly where catastrophe is otherwise rarest, which is the opposite shape from
    a size sort. **AND IT IS THE MIRROR IMAGE OF `V6-B` M1's GRADIENT** (-14.287pp smallest against
    -3.787pp megacap), whose standing caveat is *"the claim is strongest exactly where the product
    is not."* **This claim is strongest exactly where the product IS.** Both caveats are now on
    record pointing opposite ways.
  * **THE RATIO IS STABLE AND THE ABSOLUTE DIFFERENCE IS NOT, WHICH DECIDES WHAT MAY BE QUOTED.**
    The base rate is era-dependent - kept **0.3413% early against 1.3595% late**, a 4x move spanning
    COVID 2020Q1 and 2022 - so the absolute gap swings **0.86pp -> 2.39pp** while the ratio barely
    moves (3.42 -> 2.93). The flag scales the market's own crash frequency **multiplicatively**
    rather than adding a constant. **A card quoting "1.6pp more likely" would be quoting an era
    average that describes neither half. Quote the ratio and both rates; never the difference.**
  * **ONE GENUINE STRENGTH, RARE HERE: the thresholds were not fitted on this data.** -1.78, 1.81
    and the top decile are Beneish's and Altman's **published** values; this panel chose none of
    them. C5 is clean too - the largest mean per-date |rho| against any of the nine panel themes is
    **`quality` -0.1858**, far under the 0.50 bar, so it is not a repackaged incumbent.
  * **THE AUDIT'S OWN PRODUCT SENTENCE WAS WRONG AND IS NOW CORRECTED WITH A MEASUREMENT.**
    `VALQUO_MASTER_AUDIT.md:950` proposes displaying *"names tripping 2 of 3 fell **20%+** in a
    quarter **2.66%** of the time against **0.87%**"*. Those rates are the **-50%** rates -
    `S10_ACCOUNTING.json` records `"threshold": -0.5` - so **the audit paired the -50% RATES with
    the -20% THRESHOLD.** Measured at -20%: **16.845% against 8.976%, ratio 1.877x**. It is wrong in
    the direction that **discredits the card**: a 20%+ quarterly fall is ordinary, and a 0.87% base
    rate for it is transparently impossible. **Shipping it verbatim would have published a number
    that refutes itself.** Found BEFORE measuring and fixed in the register, which is the only
    reason -20% could be reported as a correction rather than chosen as an arm.
  * **A PASS IS THE WEAKER OUTCOME AND THE REGISTER SAID SO BEFORE ANY NUMBER WAS READ.** The
    full-sample separation was already published, so a fail would have been genuinely surprising and
    a pass largely confirms something visible. **What is genuinely new is that it replicates in both
    halves against its own null, survives the size control that killed three sibling items, and is
    not a repackaged incumbent.** **Expectations: 2 predictions, 2 WRONG** - C4 was registered at
    ~50/50 as the likely failure and passed 5/5 with the gradient inverted; Altman was registered as
    carrying ~70% of the separation and all three flags are comparable (2.481x / 2.565x / 2.078x).
  * **TWO DEFECTS IN MY OWN INSTRUMENT, BOTH CAUGHT BY GUARDS BUILT TO CATCH THEM.** (1) The first
    run scored **nine** panel themes at **W = 1/7**; the deployed composite is **seven at 0.125**.
    C1 came back with alpha **0.0499 against the published 0.0717** and **aborted before any arm** -
    nothing would have raised, it would simply have measured a different book under the right name.
    **The first time C1 has actually fired in this lane.** (2) The point-in-time fixture tampered
    with a future filing by multiplying every line item by 97 - and **Altman Z is a sum of RATIOS,
    so scaling a whole filing leaves it bit-identical**; the look-ahead guard would have passed
    while moving nothing. Only the companion vacuity test (*the same tamper dated BEFORE must move
    the score*) exposed it.
  * **C7's ELIGIBILITY SENSITIVITY, and the finding survives it: 25,079 rows (22.01%) carry fewer
    than TWO computable inputs and so CANNOT be flagged at all**, sitting in the base-rate group by
    construction. Re-read on eligible rows only the ratio is **2.9791 / 3.0580 / 2.9301** against
    the registered 3.0422 / 3.4209 / 2.9321 - all three still clear the 2.0x bar, with the early
    half moving most (3.42 -> 3.06). **The registered arm is on all rows and did not move.**
  * **NOT DONE, named so it is not mistaken for done: THE CARD IS NOT BUILT.** The register's
    deliverable is the *sentence*; shipping a surface is a product change and belongs to the app
    lane, with the `BANNED` phrase tuple asserted against the **RENDERED payload** rather than the
    source (`dip_posture.py`'s design). **The 4-flag rule is NOT closed** - this is 2-of-**three**,
    NT notices being unbuildable, so the flag is NARROWER and a pass does not license the audit's
    2-of-four. **No distress/delisting arm** (`V6-B` M2 is underpowered by construction at 42 events
    against a floor of 60, declined by name). **`MA27`, `MA55`, `MA57` and `MA58` were not touched**
    - running the five design-recorded items as a batch would be a five-arm search dressed as a
    backlog. **108 suites, 0 failures; 12 new tests, 3 of 3 tripwires mutation-tested.**
    `scripts/ma28_riskcard.py`, `data/free_analysis/MA28_CARD.json`;
    `HANDOFF_edge_audit.md` MA28-CARD.
- **AUDIT #3 IS EXECUTED - ALL 60 ITEMS ADJUDICATED, ZERO OPEN - AND THE LAST NINE CLOSE ON
  FINDINGS THAT REFUTE FOUR OF THE AUDIT'S OWN CLAIMS, THREE OF THEM IN THE DIRECTION THAT WOULD
  HAVE STOPPED A READER (2026-08-16, `MA24`+`MA26`+`MA27`+`MA28`+`MA33`+`MA54`+`MA55`+`MA57`+
  `MA58`).** The final batch, taken together because the record items touch documents only and the
  proposals touch `_KEEP` at most, so nothing needed `fundamental_panel.py` opened for a second
  owner. **Zero trials, all nine `FIXED`-class** - no hypothesis, no threshold, no verdict against
  a bar - so **equity `N` stays 230**, options 294, infra 15, `by_domain` is bit-identical across
  the log append and `rows_fixed_not_counted` rises **53 -> 62**, the proof the rows were seen and
  correctly excluded. **`BACKTEST_RESULTS.json` needs no re-run and no published claim moves.**
  **FINAL COUNTS: 60 items - 53 `DONE`, 5 `DESIGN-RECORDED`, 1 `BLOCKED` on the Cowork lane
  (`MA18`), 1 `PARTIAL` blocked on `MA11` and routed to Don (`MA60`). None `OPEN`.**
  * **`MA33` - THE HEADLINE JUSTIFICATION FOR THE MONTHLY REBUILD IS REFUTED BY ARITHMETIC ON THE
    AUDIT'S OWN KILL CONDITION, AND THIS IS THE BATCH'S MOST CONSEQUENTIAL FINDING.** The audit
    calls the rebuild the thing that *"unlocks the whole [text] class at once"* and re-opening
    `S19` *"the strongest argument for paying for that rebuild"*. `MA24` pre-committed the
    condition in writing: *"if the monthly panel's own MDE still exceeds +0.0096 ... close
    permanently rather than re-opened a third time."* **THE CONDITION FIRES.** `S19`'s minimum
    detectable effect is **DERIVED from its own artifact rather than quoted** - `S19_MDNA.json`
    stores no MDE key, but `MDE(|t|=2) = 2*IC/t`, and A1's
    `2 x 0.012202150018043164 / 1.1876022080477582` reproduces the record's **+0.020549 to fifteen
    digits** (A2 gives +0.031026). Rescaled to the MD&A window's **114 months** it is **+0.012324,
    still above the +0.009607 effect**; the corpus would need **188 months - 15.6 years, i.e.
    ~2032**. **The rescaling is the OPTIMISTIC bound** - monthly 63-day forward returns overlap and
    `R9` measured lag-1 **+0.189** on this project's own spread, so the true MDE is worse - **so
    the condition fires a fortiori. `S19` IS CLOSED PERMANENTLY ON `MA24`'s OWN PRE-COMMITTED
    TERMS**, and no rebuild changes that before roughly 2032.
  * **A TRAP FOR ANYONE CHECKING THAT, AND IT READS AS A FLAT CONTRADICTION UNTIL YOU KNOW IT:
    `S19_MDNA.json` ships `underpowered: false`.** That flag is the register's **COVERAGE** gate
    (`min_covered_dates` 24, `min_heldout_names` 100, `min_names_per_date` 30, all passed) and is a
    **different quantity from the MDE**. Read as a power verdict it contradicts the write-up's
    *"the design could not have returned a positive verdict even if the effect were exactly true."*
    **Both are right; they are two power concepts and only the weaker one was stored.**
  * **WHAT IS STILL TRUE ABOUT THE REBUILD, so this is a scoping memo and not a rejection.** It is
    **feasible on owned data** - `bulk.prepare_daily` already down-samples DAILY to **one row per
    ticker-month**, so monthly is the *native* granularity of the point-in-time market-cap path -
    at roughly **3x** the 69-date build's ~20 minutes, on every build thereafter. But **every X7
    calibrated bar would become an EXTRAPOLATION** (2.2837, 2.7072, 1.8629pp, 19.667% are
    calibrated for THIS panel and 69 dates), so **a monthly panel needs its own placebo sweep
    before it can carry a verdict and that cost is not in the audit's estimate**; and it inherits
    `S8`/`S9`'s `prepare_daily` staleness defect - the point-in-time market cap can be **up to 31
    days stale** against a same-day price, which on a quarterly panel is a precision defect and on
    a monthly one is **a third of the rebalance interval.**
  * **`MA57` - THE AUDIT CALLS IT THE HIGHEST-EV UNTESTED EQUITY ITEM AND THEN ATTACHES A DATA
    BLOCKER THAT DOES NOT EXIST.** It states the columns *"cannot be built without adding them and
    re-exporting **while the Sharadar entitlement is live**"*. **Measured on the export already on
    disk: `data/backtest/insiders.csv` has 24 columns, BOTH `ownername` and `transactioncode`
    present, 5,636,964 rows spanning 1980-11-25 -> 2026-07-24, 69,277 distinct `ownername`, and
    ZERO missing on all 124,181 open-market purchase rows.** No re-export, and the entitlement
    question is irrelevant: `_KEEP["insiders"]` is a six-column allowlist and the loader drops
    everything else, which is why they read as absent. **It is a ONE-LINE change** - and the audit
    verified the allowlist correctly, then drew the wrong conclusion about the file behind it.
    Cohen-Malloy-Pomorski's routine test gives **42,537 of 87,318 (`ownername`, ticker) pairs =
    48.72% routine on all coded rows** - the population their rule corresponds to, since they
    classify from any trade - and 6.93% on purchases and sales alone. **Coverage is the register's
    first control and it is not small: `transactioncode` is absent on 1,544,490 rows (27.40%)**,
    and a blank code can be classified neither way. **The `_KEEP` change is DELIBERATELY NOT TAKEN**
    - two columns with no consumer are dead weight on a 580 MB load, and the COVERAGE RULE's
    discipline is to add source columns *when the signal that needs them is added*.
  * **A DEFECT I PREDICTED AND THEN REFUTED BY MEASURING IT, reported because it ran against my own
    hypothesis.** `_insider_score` computes `val = (sh x pr) if both present else transactionvalue`;
    `transactionshares` is **signed** (2,216,036 negatives) while `transactionvalue` is **unsigned**
    (0 negatives in 2.6M), so the fallback should be scoring sales as buys. **It fires on 2 rows of
    5,636,964, neither a sale.** The branch is effectively dead and the live insider score has no
    sign defect. The same pass independently reproduced `V6-B`'s **2,182,601** silently-skipped
    rows exactly. **Reported not repaired in passing:** `_KEEP["insiders"]` requests a column named
    `date` and the export has none - it is `transactiondate` - so `filingdate or date` has a
    fallback that **can never fire**. Harmless today; the COVERAGE-RULE class; pinned rather than
    tidied.
  * **`MA26`-C - THE ROW'S DELIVERABLE WAS *NAMING THE BLOCKER* AND THERE IS NO BLOCKER TO NAME.**
    The audit says the withholding state is *"**NOT TESTABLE** point-in-time, and this is the
    finding"*, on the strength of `V6`'s result that the live sub-scores are not computable
    historically and `S23`'s that the path fetched **live Yahoo prices to value 1999**. Both are
    true and **neither binds this arm**: `withhold_implausible_fair_values` triggers on exactly one
    thing, `fair_value / price > FV_BAND_HIGH` (5.0, imported from `engine.pipeline` so the two
    surfaces cannot drift), and reads **no sub-score, no WACC and no quote**. `S23` also fixed the
    network problem itself - the valuation panel has an explicit offline mode and **asserts zero
    network calls**. **Measured on the banked panel, 2009-01-15 -> 2026-01-28: 108,100 of 108,241
    rows (99.87%) carry both columns and 5,403 = 4.998% would have been withheld, on 69 of 69
    dates**, per-date share 2.04% to 18.68%. It is a measured, dated, per-name **historical** state.
    **Two limits travel with it:** the panel's `fair_value` is `S23`'s reconstruction and not the
    value the live site published that day (nothing recorded that - `LA1`'s class, `MA29`'s
    surface), and turning a 5% base rate into a predictor is a hypothesis needing its own register.
  * **ONE EFFECT IS FILED UNDER THREE IDS ACROSS TWO PASSES, AND THEY WANT ONE REGISTER.**
    `MA26`-A (accounting flags as a disclosure), `MA28` (the same as a product card) and `MA54`-1
    (the same re-examined on `V6-B` M1's instrument) are **the same object**; building three would
    triple-charge one hypothesis. Folded into a single `MA28` register: gate on the **crash-rate
    replication in both halves and NOT on alpha** (`S10-ACCT` failed the portfolio-drawdown leg,
    and `S10` had already measured this book's max drawdown to be **one** market-wide quarter,
    COVID 2020Q1 at trough index 44 of 69, that no name-level flag can move); instrument = `V6-B`
    M1's; **mandatory** market-cap control; a `BANNED` phrase tuple asserted against the **rendered**
    payload. **One caution measured for the memo: `S10-ACCT` ran 2-of-THREE, not the audit's
    2-of-four, because NT late-filing notices are unbuildable - so a null on 2-of-3 does not close
    the 4-flag rule**, and the register must say so before it runs rather than after.
  * **`MA54` IS RECONCILED AGAINST THE OPTIONS FRONTIER RATHER THAN DUPLICATED, AND ITS BIGGEST LEG
    WAS ANSWERED BY ANOTHER LANE THE SAME DAY.** **-2 (`O17-C4` "own the event") IS ANSWERED AND
    NOT BY THIS BATCH**: re-registered as its own strategy (`PREREG_o17c4_own_the_event.md` alone at
    `aeca6f0`), ledger row **`O17C4` = REJECTED on c3** with c1/c2/c4 passing, options `N` 292 ->
    294 - and **the effect is real and survives the alert's death**, +10.30% against +5.50% on
    27,350 random-entry control trades, **+4.79pp**, both halves, sign **z +2.054, p 0.040**. **This
    lane deliberately does not re-measure it**; duplicating a landed measurement is how two lanes
    come to publish two numbers for one question. **-1** folds into `MA28`. **-3** is `NEEDS-DATA`
    (~4.7 GB pull; the cache is alert-days-only so a same-design re-run is impossible by
    construction). **-4 IS ORPHANED BY ITS OWN VEHICLE** - the frontier routed its remedy into
    `P1`'s register, and **`P1S0` then FAILED at its power anchor and the options-expression family
    CLOSED**, so the remedy is sound and has nowhere to live. **The disagreement the frontier
    reported rather than resolved is now resolved in the frontier's favour.**
  * **`MA55` AND `MA27`'s PREMISES BOTH HOLD, WHICH IS WORTH SAYING BECAUSE THREE OTHERS DID NOT.**
    `MA27`: `per_signal.signals` carries **exactly 53** entries and `NUMBER_THEME` 53, and its three
    arguments distinguishing KNS ridge from `S5`, `MLCOMB` and the eight `_weight_schemes` hold on
    inspection. `MA55`: the banked panel carries three lens columns (99.87% / 100.00% / 74.55%), so
    the disagreement width is computable on **108,100 of 108,241 rows with ZERO zero-width rows**
    (p05 0.1195, median 0.8777, p95 4.1069). **The `w_floor` is LOAD-BEARING and the measurement is
    why: the width's maximum is 3,585, four orders of magnitude above its median** - without a floor
    the arm becomes a *disagreement* screen rather than a precision-weighted mispricing signal.
    **A correction both registers must carry: the audit quotes the alpha margin as 1.95pp and
    `MA19` recalibrated it to 1.8629pp** at `N` = 224 nine days ago - and `MB31` proves it is
    **unmoved at every equity `N` below 247**, so it is current today without needing a date.
  * **`MA58`'s PREMISE HOLDS, WITH THE `MA23` LESSON ATTACHED: A NAME MATCH IS NOT A PAPER CENSUS.**
    Every *"seasonal"* hit in the corpus outside the audit documents is **fiscal-quarter seasonality
    in fundamentals**, and `NUMBER_THEME`'s 53 entries contain no seasonality-shaped key - so the
    audit's *"zero mentions"* holds in substance. But **`Linnainmaa` appears TWICE in
    `VALQUO_EDGE_AUDIT.md`**, for Ball-Gerakos-Linnainmaa-Nikolaev's cash-based operating
    profitability and Ehsani-Linnainmaa's factor momentum - neither of which is
    Keloharju-Linnainmaa-Nyberg. **A grep for the AUTHOR would have read as "already covered".**
  * **A DEFECT IN MY OWN INSTRUMENT, FOUND BY DISBELIEVING A ZERO.** The blank-code counter first
    read **0** on a column with **1,544,490** of them: under pandas' string dtype a missing cell is
    `pd.NA`, `astype(str)` leaves it `NA` rather than producing `"nan"`, and **`NA` compares False
    against every literal** - so the check asked a question the data could not answer and got a
    clean, confident zero. **The vacuous-pass family in a new costume**, and the same language
    feature produced a *correct* exclusion two lines away in the pair census, which is exactly why
    it was caught by the number looking wrong rather than by anything raising.
  * **A DEFECT IN THE AUDIT'S OWN CROSS-REFERENCE:** row 8 of its section 10 table says *"the unlock
    is **MA24's** monthly rebuild"* while its own id map eleven lines above assigns the monthly
    rebuild to **`MA33`** and `MA24` to *"Wrong rejections"*.
  * **WHAT THIS DOES NOT SAY, and it is the most likely misreading: `DESIGN-RECORDED` IS NOT A
    FINDING THAT AN ARM WOULD FAIL.** `MA26`-A/B, `MA27`, `MA28`, `MA55`, `MA57` and `MA58` are
    **NOT RUN**; each is a live question and needs its own blind pre-registration committed ALONE
    first. The one thing that closes permanently is `S19`, and it closes on `MA24`'s own
    pre-committed kill condition rather than on this batch's judgement. **107 suites, 0 failures;
    16 new tests, 3 of 3 tripwires mutation-tested.** `DESIGN_ma_final_batch.md`,
    `data/free_analysis/MA_FINAL_BATCH.json`; `HANDOFF_edge_audit.md` MA final batch.
- **THE AUDIT'S OWN EVIDENCE IS WRONG IN TWO OF THESE FIVE ITEMS, AND IN BOTH CASES IT IS WRONG
  IN THE DIRECTION THAT WOULD HAVE MADE A READER STOP (2026-08-16, `MA14`+`MA21`+`MA25`+`MA34`+
  `MA49`).** The wave-2/LOW pipeline batch, sequenced severity-then-collision. **Zero trials, all
  five `FIXED`-class** — no hypothesis, no threshold, no verdict against a bar — so **equity `N`
  stays 227**, `by_domain` is bit-identical across the log append and `rows_fixed_not_counted`
  rises **47 → 52**, the proof the rows were seen and correctly excluded, and **no published claim
  moves.**
  * **AND THE ANSWER TO THE STANDING QUESTION IS NO: `MA23` DID NOT WIDEN THESE BATCHES, AND IT
    NEVER COULD HAVE.** `fundamental_panel.py` is **5,014 lines, byte-for-byte what it was before
    `MA23` landed** — the move relocated the directory's OTHER occupants, and the panel is a file
    that was never among them. `MA14` and `MA25` still had to share this session because they
    share that file. The map's headline calling `MA23` "the item that would change" the
    one-owner-at-a-time rule remains the correction shipped last session, now demonstrated
    operationally rather than only by line count.
  * **`MA34` — THE AUDIT REASONS FROM A RUN THIS FILE MARKS VOID, AND THE PARTITION COMES OUT
    BACKWARDS.** Its verification cites *"SMB +0.39 t 3.84, RMW +0.30 t 4.49, UMD +0.18 t 3.49"*
    with HML and CMA at t 1.08, concluding a post-publication decay prior attaches to `size`,
    `quality` and `momentum`. **Those figures reproduce BIT-FOR-BIT from
    `data/free_analysis/FACTOR_ALPHA_RESULTS.json`** — SMB +0.394 (t +3.84), RMW +0.298 (t +4.49),
    UMD +0.181 (t +3.49) — **at `n_periods` 109, which is the pre-B6 110-date panel**, the run
    whose own bullet below reads *"DO NOT QUOTE IT."* On the corrected panel **HML +0.251 (t
    +2.93) and UMD +0.205 (t +3.65) LOAD while SMB +0.208 (t +1.39) and RMW +0.092 (t +0.90) do
    NOT**, so **the prior attaches to `value` and `momentum`** — 2 of 7 weighted themes, **28.6% of
    the effective composite** — and not to the two the audit names. The audit's FORM survives; its
    partition is inverted. Registered as `PAPER_TRACK_CONTRACT.md` **§6.6**, before the window
    accrues, which is the only time an expectation is worth anything.
  * **NO MAGNITUDE IS ISSUED AND REFUSING IS THE POINT.** 28.6% decaying by a third reads as
    +9.99 → ~+9.0 pp/yr, and that arithmetic assumes a theme's contribution is proportional to its
    weight — **which X3 measured to be FALSE**, `size` having the worst theme IC (−0.30) and
    carrying the composite's entire significance. **Direction and affected fraction are
    registered; the magnitude is not.** One consequence is recorded because it runs against the
    strategy: §6.2's power table is computed **at** the backtested +9.99pp/yr, so if the prior
    holds the **real power is BELOW the stated 13.3% at 60 months.**
  * **`MA25` — THE RECORD CORRECTION IS CONFIRMED AND THE AUDIT UNDERCOUNTS ITS OWN EVIDENCE BY
    73%.** *"There is no liquidity measure on this path"* is **true of the panel and false of the
    project**. Measured, not quoted: `data/bulk/prepared/bars/*.pkl` holds **502 names** — the
    audit and `capacity.py`'s own header both say 290 — every one carrying `volume` and
    `raw_close`, **2,780,252 rows**, spanning **1997-12-31 → 2026-08-07**, i.e. the whole panel
    window, all 502 present in DAILY, **19.8% of the 2,531-name universe**, median $ADV $150M.
    `capacity.py::adv_from_bars` already computes it. **Corrected in the shipped ARTIFACT rather
    than only in prose** — `prefilter_note` carries it and a new `prefilter_adv_partial_source`
    block ships the numbers — because a reader of `BACKTEST_RESULTS.json` was the one being
    misled. **B13 and S7 are NOT overturned**: 80.2% of the universe still has no measure so the
    filter cannot bind universally, and S7 was right to refuse a proxy. **THE TEST IS
    DELIBERATELY NOT RUN**, on the audit's own recommendation.
  * **`MA21` — ONE OF ITS FIVE CONVENTIONS IS REFUTED BY THE ARTIFACT IT PROPOSES TO CHECK.** It
    asks that an unknown verdict become a warning. `build_ledger.py`'s own *"How to read a row"*
    states blank means *"not measured, or measured and reported in different words — never 'we
    don't know'"*, and **41 of 230 DONE rows carry a blank verdict**, every one legitimate. The
    warning would fire on all 41 plus every prose verdict and be switched off inside a week — the
    cry-wolf failure `MA19` already refused once. **A substitute ships**: the vocabulary literal
    and the documented list are two copies of one fact in one file and must not drift.
  * **THE OTHER FOUR: one was already done, two are enforced, one cannot be.** (1) is **MA13's**
    and is not re-implemented, because a second pin is a second definition. (2) the artifact-vs-log
    check is **enforced in the one direction that cannot cry wolf** — trials only accumulate, so
    the artifact may LAG the log and may never LEAD it; **the drift is live at 3** (artifact 224
    against a live equity 227) with nothing whatever wrong, which is exactly why equality would be
    the wrong test. (4) reads clean — 46 MA ids across 400 commit subjects, all with rows. (5)
    scheduling M4's fidelity harness is **REPORTED, NOT TAKEN**: it needs a `.github/` edit
    `land_policy.py` refuses by design **and** the licensed export CI must never hold, so it is
    blocked twice over. **All three tripwires MUTATION-TESTED 3 of 3** — a tripwire that cannot
    bite is not a check.
  * **`MA14` — THE PORT, AND THE ONE PLACE IT DELIBERATELY DIFFERS FROM THE BACKTEST VERSION.**
    Verified first: `sanity_check` is reachable only from the backtest and `optvrp_report`, while
    the live health block carries `theme_coverage`, which answers PRESENCE. `OOB2` is what the gap
    costs — one dropped Yahoo beta field, a 1.10 default, and MRK went from *"cannot value"* to a
    **91 Strong Buy** with nothing empty and nothing raised. The bands now live in a
    dependency-free `sanity_spec.py` that `fundamental_panel` **re-exports** (MA39's pattern, so
    the 5,000-line engine never reaches the request path and every existing importer is
    untouched), and a test pins **object identity** plus **exactly one literal assignment in the
    tree**. **The difference: `sanity_check` silently skips an absent column**, which is right for
    a panel built to a known schema and catastrophic on a live frame, where a rename would produce
    zero checks and an empty `flags` — a clean bill of health from a guard that looked at nothing.
    `columns_absent`, `checked` and `vacuous` close that. Demonstrated on P7's signature: a 892
    `book_to_price` fires **both** the range band and the foreign-subgroup peg. Reporting-only,
    pinned.
  * **`MA49` — FIVE LATENT DEFECTS, AND FOUR OF THE FIVE FAIL IN THE FLATTERING DIRECTION.**
    **(a)** the factor coverage bar is hard-coded at 2025 and is **left frozen deliberately** —
    it is PRE-REGISTERED, and a registered bar that follows the clock is not the bar registered —
    so staleness ships as a **reported number** instead; its live companion is that
    `factor_windows` dropped an uncovered window with a bare `continue`, silently **shortening
    every regression in the file**, now counted. **(b)** `sharpe` filtered `None` and not NaN
    while `_clean` in the same module drops both, so one NaN returned **NaN** and
    `deflated_sharpe_ratio` carried it to a published verdict — **a value that compares False
    against every bar, failing a threshold in silence.** Reproduced, then fixed by delegation;
    **inert on the shipped inputs at max abs difference 0.000e+00 over 2,000 NaN-free series**,
    DSR unchanged at 0.7863213339664521. Its second half, `trial_sharpes and len(...) > 1`,
    **raises** on an ndarray, so the documented argument worked for a list and crashed for the
    type every caller holds. **(c)** `n_names = 9  # 8 schemes + current-default` — the comment
    states its own error, `_weight_schemes` returns **8** with `current-default` among them, so
    the n=8 point was scored at √(2·ln 9)=2.0963 rather than 2.0393; now **derived**, not
    re-typed. **(d)** the `ex_b6_first_37` cut ran regardless of `--corrected-panel`, mislabelling
    37 healthy dates as contaminated — **while its sibling block 56 lines earlier already branches
    on that flag and explains why in a comment.** **(e)** `_cap_mask` returned the **full
    universe** for a tier it could not form, wider even than the finite-cap names, so a
    tier-labelled date contributed everything: **B12's defect — a count read as an identity — in a
    different column.**
  * **AND THE SAME DEFECT IN MY OWN GUARD FOR THE THIRD TIME IN TWO SESSIONS.** The `MA49(c)`
    fixture grepped for `n_names = 9` and **failed against the FIXED tree**, because the comment
    documenting the repair quotes the defect verbatim. Comment-versus-code, after `MA5`'s source
    sweep and last session's boundary test. It reads the **AST** now. **A fourth instance of the
    family, in the ledger this time:** the `MA49` note carried a raw `|` inside `|old-new|`, which
    split the row into 12 cells and made `MA49` **vanish from `build_ledger`'s id list** — the
    `M1-PARSE` hazard, committed with the warning in view.
  * **PINNED: 13 of 15 fixtures fail against the pre-fix tree.** The two that pass are reported as
    passing deliberately — one **is** the NaN-free inertness proof (it must agree before and
    after) and the other pins a pre-existing consumer guard the `(e)` fix relies on. **MA21's 8
    pass pre-fix too, and that is not a weakness**: it changes no source, so its tests are
    tripwires, which is why they were mutation-tested instead. **DEFERRED AND NAMED SO THEY ARE
    NOT MISTAKEN FOR DONE: `MA24`, `MA26`, `MA27`, `MA28`, `MA33`, `MA54`, `MA55`, `MA57`, `MA58`
    — all nine charge trials and need a blind pre-registration**, which is what the register
    exists to prevent a correctness batch from skipping. **102 suites, 0 failures; 23 new tests.**
    `HANDOFF_edge_audit.md` MA14+MA21+MA25+MA34+MA49.

- **THE OPTIONS-EXPRESSION FAMILY IS CLOSED AT ITS GATE: THE EQUITY COMPOSITE SORTS THE
  OPTIONABLE UNIVERSE ONLY AFTER 2021, AND A FULL-SAMPLE READING WOULD HAVE LICENSED THREE
  SESSIONS ON IT (2026-08-16, `P1S0` + `U6-COV` + `O17C4`).** Executes
  `VALQUO_OPTIONS_FRONTIER.md` (a read-only design by a separate session).
  `PREREG_p1s0_optionable_gate.md` committed **ALONE at `f4ddd8b`**;
  `PREREG_u6_overwrite_leg.md` + `PREREG_o17c4_own_the_event.md` together and **ALONE at
  `aeca6f0`**. **ADOPTS NOTHING.** **Equity `N` 227 -> 230, options 292 -> 294**, infra 15.
  * **THE FRONTIER'S HEADLINE IS CONFIRMED FULL-SAMPLE AND IS NOT A BASIS FOR ACTION.** On the
    point-in-time optionable universe the composite sorts strongly over the whole covered window
    - **H=63 cumulative +3.51%/quarter (+14.05%/yr) at HAC *t* 3.3731 against its own calibrated
    floor of 1.4822** - so *"the composite does NOT weaken on optionable names, it strengthens"*
    reproduces on the **shipped** instrument and a PIT partition. **Then it fails the both-halves
    rule at EVERY horizon, always the same way: H=63 early *t* 0.8352 vs 1.6974 FAIL / late
    4.1471 PASS; H=252 early -0.0379 FAIL / late 2.8778 PASS; H=504 early 0.4570 FAIL / late
    1.9351 vs 2.2028 FAIL.** The early half (2016-2020) is **absent** - at H=252 its cumulative
    alpha is literally **-0.08%** - while the late half reads **+24.31%/yr** at H=63. **THE
    OPTIONABLE-UNIVERSE EDGE IS A POST-2021 PHENOMENON**, and `V6`'s warning applies verbatim.
  * **IT IS A GENUINE FAIL, NOT A POWER ARTEFACT, which is why a THREE-STATE grammar (PASS /
    FAIL / UNDERPOWERED) was fixed before any number existed.** `design_can_see_the_known_effect`
    is **TRUE at all three horizons** - the observed effect and the reference effect (the full
    panel over the SAME dates, `MA31`'s C-POWER pattern) both exceed the MDE **even at H=504**,
    where the covered sample carries only **~4.25 independent observations**. The kill fires on
    **H=63, 40 dates at ZERO overlap** - a horizon the frontier did not specify and which was
    ADDED precisely because H=252 and H=504 could not have returned an interpretable null.
    **The sensitivity universe agrees at all three horizons.**
  * **THE INSTRUMENT IS THE SHIPPED ONE AND THE FRONTIER'S WAS NOT.** S22's `arm()` reproduces
    `C1_RECORD`'s `top_decile_alpha` at abs delta **1.84e-14** and three further fields at
    **exactly 0.00e+00**, where the frontier's own reached +7.48% against +7.17%. Cause
    diagnosed, not assumed: its deciles use `nlargest(len//10)` against the shipped
    `array_split`, so the two do not hold the same names. **Two corrections to its arithmetic:
    1,000 raw ticker dirs, not 1,044** (44 non-directory entries), **906** of them in the panel.
  * **WHAT CLOSES: P1 (deep-ITM long-dated calls), P3, U6's overwrite arm, and any future
    attempt to express the equity book in derivatives.** No option was priced, **no LEAPS re-mine
    was run, and `D2`'s licence question does NOT need putting to Don** - there is no pull.
    **What does NOT close: the equity composite on the FULL panel is untouched** and its published
    figures stand; and the frontier's §2c financing arithmetic (rf + 43 bps) is neither retested
    nor refuted - it simply has nothing left to finance.
  * **`U6`'s BLOCKER IS MEASURED AGAINST THE WRONG UNIVERSE - AND THE RE-OPEN'S OWN PREMISE IS
    ALSO WRONG. ZERO TRIALS.** It was to be re-opened because the 1.81% counted decile ENTRIES
    while an overwrite is written on HOLDINGS. **Refuted: entries 648/7,138 = 9.08%, holdings
    897/11,426 = 7.85%, so holdings are 0.86x as well covered as entries**, not the 6-11x
    assumed. **The real error is the DENOMINATOR OF NAMES** - the row's own text says it was
    measured *"against the 187-name mined universe"*, the ALERT universe, while the cache holds
    **906 panel names**: universe ratio **4.84x**, coverage ratio **5.02x**, agreeing to within
    4%. **And it is UNDERSTATED, because it runs against a STRICTER test** (a chain must exist
    ON THAT DATE, not merely at all). Two controls make it like-for-like: entry events **7,138
    against the row's 7,132**, and top-decile membership **11,426 - exactly the count `S10` and
    `V6-B`'s C7 report independently**. **The CSP entry leg is untouched and the row's status does
    not change**; the overwrite leg is buildable (median 12 PIT-liquid / 21 any-chain holdings per
    covered date, **zero covered dates with none**) and **BOUNDED at 7.3-13.0% of decile slots**.
    Part B was gated on Stage 0 and Stage 0 closed it.
  * **`O17`-C4 "OWN THE EVENT" IS REAL AND SURVIVES THE ALERT'S DEATH - AND THE ALERT STILL
    SUBTRACTS VALUE INSIDE IT.** Its `NULL` rested SOLELY on a 0.70 retention floor set for a
    product reason. The bar was **DERIVED first, not lowered** (`TP-BAR`'s procedure-not-a-number
    rule). The decisive test had never been run and was runnable on owned data: as a FILTER its
    null is random-REMOVAL, but as a STRATEGY the comparator must be random ENTRY. **On 27,350
    random-entry trades a call spanning the next announcement earns +10.30% against +5.50%, a
    +4.79pp gain, positive in BOTH halves, sign test *z* +2.054 (p 0.040)** - so it is a property
    of owning an earnings event, not of the alert. **But alert-spanning +8.42% LOSES to
    random-spanning +10.30% at *z* -4.4726, p 7.7e-06** - `R2` reproduced inside the very subset
    meant to rescue it - **so the strategy is "buy calls spanning earnings" with NO ALERT IN IT AT
    ALL.** **It is a MEAN effect, not a MEDIAN one**: DTE-matched, the mean clears a shuffled null
    on both books while **median-vs-median is +0.40pp** (-51.41% against -51.81%); the typical
    trade is a near-total loss either way. `O11` governs - **nothing here licenses trading it.**
  * **THREE DEFECTS IN MY OWN INSTRUMENTS, ALL CAUGHT BY RUNNING THEM, AND ONE HAD ALREADY BEEN
    REPORTED AS A FINDING.** (a) Stage 0's C2 compared pandas **dtypes** rather than values and
    failed a bit-identical partition, because `pit_liquid` is TRI-STATE - it failed in the SAFE
    direction and was still wrong, and its probe was all-`True` so it exercised neither the `None`
    nor the `False` branch. (b) **Two of O17-C4's three registered bars do not measure what they
    were written to**: B1's trades-per-year axis is **unpassable by construction** for a subset of
    the book it is drawn from, and B1/B2's NAME axes re-measure the **29-name foreign-issuer
    coverage hole** (the spanning set is capped at 157 names and touches all 157). Only B3
    measured its property, and it **passes**. **So a result that was NULL only because of a bar
    set for a product reason is now REJECTED only because of a bar that was broken.** (c) **The
    DTE-matched MEDIAN is an ARTIFACT and was reported once as a finding before being caught** -
    comparing one draw against the MEAN of a right-skewed set is biased low by construction, and
    the shuffled null median is **-41.9pp against a real -35.8pp**, so the real figure runs
    slightly IN THE ARM'S FAVOUR and the reading was exactly backwards. All three registers are
    left **UNEDITED**; the diagnoses ship beside them.
  * **A CORRECTION TO THIS PROJECT'S OWN FOLKLORE, measured while appending to the log: an
    unescaped `|` in a research-log cell CANNOT be fixed by writing `\|`.** More than one handoff
    records that such pipes *"want escaping as `\|`"*. `research_log._parse` splits on a bare
    `"|"` and honours no escape, so `\|` still shifts every column and is flagged
    `rows_malformed` exactly as an unescaped pipe is. **The only fix is not to put a pipe in the
    prose.** Caught because the `P1S0` row used `|delta|` for an absolute value.
  * **Expectations: Stage 0 scored 6 right, 2 wrong** (the anchor was predicted to PASS; at least
    one cell was predicted UNDERPOWERED and none is). `data/free_analysis/P1S0_GATE.json`,
    `P1S0_CONTROLS.json`, `P1S0_COVERAGE.json`, `P1S0_OPTIONABLE_PARTITION.pkl`,
    `U6_OVERWRITE_COVERAGE.json`, `O17C4_OWN_THE_EVENT.json`, `O17C4_BARS.json`;
    `HANDOFF_optionsbot.md` 62.
- **THE LARGEST UN-RUN ITEM EITHER AUDIT NAMED IS RUN, AND THE ANSWER IS THAT THIS UNIVERSE
  CANNOT ANSWER IT - ON THE OPTIONS-LISTED SUB-POPULATION THE PANEL'S OWN BEST SIGNALS CANNOT BE
  SEPARATED FROM ZERO (2026-08-15, `MA31`+`MA32`+`MA56`).**
  `PREREG_ma31_ma32_parity_openclose.md` committed **ALONE at `a51e372`**, a strict ancestor of
  every measurement commit. **ADOPTS NOTHING.** **Equity `N` 224 -> 227** (three arms, charged to
  EQUITY on the `U2` precedent - they predict the UNDERLYING's forward return); options stays
  **292**. **With these the options-bot lane is CLOSED on audit #3: all ten of its MA rows DONE.**
  * **A CORRECTION TO THE DISPATCH BRIEF, MADE BEFORE ANYTHING WAS MEASURED: `MA31` IS WAVE 3, NOT
    WAVE 2.** Wave 2 is *"unblocked by wave 1, **zero trial cost**"*; `MA31` and `MA32` carry
    `trial_cost 1-2` each, so they need a blind register and were kept out of the correctness
    batch. `MA56` is `trial_cost 0 (record only)`.
  * **ALL THREE ARMS NULL - AND ALL THREE NULLS ARE UNINTERPRETABLE BY THE REGISTER'S OWN
    PRE-COMMITTED POWER RULE.** `parity_dev` (Cremers-Weinbaum's OI-weighted matched-strike
    `iv_call - iv_put`) reads incremental IC *t* **-1.0886 / -0.3380** against X7's 2.71;
    `call_open_share` **-1.4146 / -0.7169** against its own permutation p95 of 1.9547 / 1.7547;
    `put_open_share` **+0.0633 / +1.0895** against 2.0879 / 2.0978.
  * **THE POWER MEASUREMENT IS THE FINDING AND IT OUTLIVES BOTH ITEMS.** The audit's bar is 2.0.
    Across three NESTED populations (raw IC *t*): `z_gp_on_capital` **+3.6745** on the full 69-date
    panel, **+2.4776** on the 40 covered dates across ALL names, **+0.9919** on the ROWS THE ARMS
    ARE MEASURED ON; `quality` **+3.1015 -> +2.8014 -> -0.0594**; `value` +0.8380 -> +0.7505 ->
    -0.0681; while **`size` flips -0.3005 -> -0.7996 -> +3.0765**. **So on the options-listed
    sub-population the project's own known-real signals do not work and `size` dominates** - `U7`'s
    finding reproduced on **906 names** rather than its 187 megacaps. **Any future options-derived
    STOCK signal on this cache inherits it: a null there means "could not be separated at this
    resolution", never "absent".**
  * **A CORRECTION TO THE RECORD, AND IT IS THIS LANE'S OWN.** This file records `U2`'s power
    control as *"gp_on_capital 2.4776 and ret_6_1 2.4762 on the identical covered rows"*. Both
    reproduce here **to four decimal places** as the covered-DATES / **ALL-NAMES** figure, on an
    identical covered geometry (40 dates, 20/19, boundary 2021-01-21) - so **`U2`'s power control
    was NOT restricted to the rows `U2`'s arms were measured on, and it overstates the power they
    had.** **`U2`'s verdicts do not change** (a weaker power control cannot rescue a rejected arm);
    its nulls were simply even less interpretable than claimed.
  * **TWO PUBLISHED SIGNS, TWO OUTCOMES. Cremers-Weinbaum's POSITIVE direction is NOT reproduced in
    any window** (every reading negative; raw *t* -1.3676) - **the third published options sign
    this project has failed to reproduce**, after `O7` and `U2`. **Ge-Lin-Pearson's NEGATIVE
    direction for the call arm IS reproduced in sign in all three windows** and fails only on
    strength, which is a more informative null than a flat one.
  * **THE TRAP NAMED IN THE REGISTER BEFORE THE RUN, BECAUSE IT WOULD HAVE PRODUCED A CLEAN
    FABRICATED NULL: `dividends.spot_from_parity` returns `S = C - P + K*exp(-rT)`, so feeding it
    back as the spot makes `iv_call - iv_put` identically ZERO BY CONSTRUCTION** and nothing would
    have raised. Forbidden by name, pinned at source. The other half is settled by measurement:
    `assert_raw_spot` matches the as-traded series at median relative error **exactly 0.0** over
    16,742 entries and **RAISES** on the adjusted one at **8.52%** (worst SIRI 36.5180 vs 3.9900).
  * **TWO DEFECTS IN MY OWN INSTRUMENT, BOTH CAUGHT BY GATING CONTROLS, AND BOTH WOULD HAVE READ AS
    RESULTS RATHER THAN AS BUGS.** The feature frames were keyed on the REBALANCE date while
    `join_pit` implements the strictly-before rule itself, so it joined **0 of 113,945 rows**; and
    `coverage_report` stringified its dates, so every consumer filtered a datetime column with
    strings and all three arms returned `n_dates = 0` **while coverage simultaneously read 40 dates
    and 16,736 rows**. Neither raised, and *"the arms have no coverage"* is a sentence this project
    has legitimately written five times. **The two-pass design - controls computed AND READ before
    any arm is scored, `--arms` refusing to run without a passing artifact - is what separated a
    bug from a finding**, and it is session 26's defect repaired rather than repeated. **A third,
    in my reporting: the MDE was first quoted beside the MEDIAN IC, which is not the statistic it
    pairs with; against the MEAN all three arms sit BELOW their own detection threshold.**
  * **CONTROLS: `MA31` is NOT `U2`'s rejected arm renamed** (Spearman **+0.3796** vs `-skew_25d`,
    against a 0.90 bar) and the two `MA32` arms are not each other (**+0.3164**, separate
    denominators by construction); **the arms carry genuinely new information and predict nothing
    with it** (R2 on the seven incumbents **0.0438 / 0.0273 / 0.0361** - `U2`'s dissociation
    reproduced); **`B4`'s `-1` sentinel is live and excluded, 931,080 contract-days**, with the
    count REQUIRED non-zero because a zero would mean the filter never reached the data;
    **C-BAND** the 0.20 moneyness band correlates +0.9215 with the primary and gives the same
    answer; **C-AMER NOT RUN and reported as not-run** rather than silently skipped.
  * **THE AUDIT'S PREMISE IS TRUE AND INSUFFICIENT, AND THE NEW NUMBER IS THE REASON.** `V6-OPT`
    removed `U2`'s blocker by measuring 1,288,750 puts against 1,288,751 calls - but **a matched
    pair being PRESENT is not a matched pair being USABLE**: it needs a two-sided quote on BOTH
    legs, so the pair-level rate is roughly the **SQUARE** of `MA45`'s leg-level one (42 of 92, 10
    of 64, **2 of 25** on sampled cross-sections). It was scoreable anyway - **16,736 rows over 40
    covered dates, median 431.5 names/date, halves 20/19, boundary 2021-01-21**, the identical
    geometry `U2` and `V6-OPT` landed on. **A correction to the audit: it says 29 of 69 dates carry
    zero coverage; against the RAW layer it is 28.**
  * **`MA56` IS RECORDED AND DELIBERATELY NOT RUN** - its own kill condition is *"do not run
    today"*, so measuring it would breach the audit's instruction, and the register makes quoting
    it as a tested result a void condition. **Zero trials** (`rows_fixed_not_counted` 40 -> 41 is
    the proof it was seen and excluded). `ts_resid = term_slope - beta*atm_front` at IC **+0.07034**
    [+0.0287, +0.1131] against raw **+0.05673**, with `-atm_front` at +0.01316 spanning zero -
    **verified against the `O16-REFROZEN` row itself, not copied from the audit's summary**, and
    written into `options_entry.py::MA56_CARRY_FORWARD` where the next entry register's author will
    be standing, pinned by a test that **re-parses the log row and fails if the record drifts**.
    **Three caveats the summary omits travel with it: the IC is measured on `R2`'s book, which
    loses to random entry by -5.0640pp/trade, so the feature has been shown to SORT A LOSING BOOK
    and not to make money; the `IS DISTINCT` verdict hinges on the pre-registered choice of
    Spearman, since Pearson reads -0.82793 and returns the OPPOSITE verdict; and it was not blind.**
  * **NOT DONE, named so it is not mistaken for done: the O/S ratio is NOT built and NOT proxied**
    (it needs stock volume, which per `MA25` exists for ~290 names), surface **changes** are
    untested (`U2`'s other declined half), and `U2`'s three rejected level arms are not re-opened.
    **Expectations 6 right, 2 wrong. 96 suites, 0 failures; 38 new tests, 36 of which fail against the pre-session sources.**
    `data/free_analysis/MA31_MA32.json`; `HANDOFF_optionsbot.md` 61.
- **SIX ITEMS THAT EACH PRODUCED A PLAUSIBLE NUMBER RATHER THAN AN ERROR — AND THE ONE THE MAP
  CALLS THE UNBLOCKER CANNOT UNBLOCK WHAT IT NAMES (2026-08-15, `MA23`+`MA40`+`MA41`+`MA42`+
  `MA43`+`MA47`).** The wave-2 pipeline batch, taken severity-then-collision. **Zero trials, all
  six `FIXED`-class** — no hypothesis, no threshold, no verdict against a bar — so **equity `N`
  stays 224 FOR THESE SIX — and reads 227 after merging the concurrent `MA31`+`MA32`+`MA56`
  landing, which is why an equity figure must be RE-READ from `by_domain` after a merge and never
  quoted from a session's own mid-run measurement**, `by_domain` is bit-identical across THIS
  batch's log append (which is also the check that
  MA13's stamp still holds, and `rows_fixed_not_counted` rises **40 → 46**, the proof the rows were
  seen and correctly excluded), and **no published claim moves.** `SCHEMA_VERSION` 6 → 7 is
  additive, so `BACKTEST_RESULTS.json` needs no re-run — the next run simply carries two more
  blocks.
  * **`MA23` — THE BOUNDARY IS DRAWN AND IT DOES NOT DO WHAT THE MAP SAYS.**
    `MA_DEPENDENCY_MAP.md`'s second headline calls MA23 *"the item that would change"* the rule
    that `fundamental_panel.py` cannot be split across owners. **Measured: the twelve study
    modules total 4,587 lines, and the panel is 5,014 lines and is NOT one of them.** Moving a
    directory's other occupants cannot shrink a file. **The constraint on the panel is untouched
    and still binds**, and a test now pins that so nobody later reads the move as having lifted
    it. **AND A CORRECTION AGAINST MY OWN FIRST DRAFT OF THIS BULLET, MEASURED AFTER WRITING
    IT: THE MOVE DOES NOT TAKE THOSE LINES OUT OF THE DEPLOY IMAGE EITHER.** The Dockerfile
    is `COPY . .` and `.dockerignore` excludes `tests` and `*.md` and nothing under
    `valuation/`, so the studies ship in the image before the move and after it — which
    means **one of the audit's own three motivations for MA23 is not met by MA23 as
    specified.** What the move does buy is the other two: the package the Flask app imports
    from no longer contains studies, and a reader can tell product from study by location.
    **The image residual is one `.dockerignore` line and is REPORTED, NOT TAKEN** — it is a
    deploy-config change whose blast radius is the running container, and `scripts/` is in
    the image and does import the studies, so excluding one without the other would break
    an in-image script. Safe to do later precisely because the test above proves no product
    module imports a study.
  * **TWO CORRECTIONS TO THE AUDIT'S OWN CENSUS, BOTH MEASURED.** It says eleven modules are
    *"referenced only by their own `scripts/` runner and their own test"*; **it holds for nine.**
    `scripts/ml_combiner.py` does **not** import `edge/ml_combiner.py` — two independent
    implementations, both defining `fit_predict`, and **the published `ML_COMBINER.json` came from
    the script**, so the module's only caller is its test. `lazy_prices_ic` has **no `scripts/`
    runner at all**. `ev_multiples_study`'s zero importers is confirmed exactly. **A name-match
    census is not an import census** — `param_search.bat` was a false hit, since it runs
    `fundamental_panel --param-search`. All twelve moved as **git renames**, nothing deleted
    (rule 9), and the engine-may-never-import-a-study direction is pinned.
  * **`MA40` — CONFIRMED AGAINST THE SHIPPED ARTIFACT RATHER THAN THE WRITE-UP.**
    `'sector_caps' in BACKTEST_RESULTS.json` → **False**, and the shipped `walk_forward` block
    carries six keys while the producer returns four, **dropping the entire trade-parameter sweep
    with its per-parameter adopt verdicts.** B21's own comment reads *"this block measures it and
    ships the numbers"* — it measured it and shipped nothing. **Registered rather than dropped**;
    both are now in `BLOCK_SPEC`, so M6's guard fails the run if either goes again. Line drift
    recorded: the audit cites `:4937`, the producer is at **`:4968`**.
  * **`MA41` — THE PREMISE HOLDS AND THE STAKES ARE HIGHER THAN THE AUDIT STATES.**
    `grep -c embargo walkforward.py` → **0**, against sibling splitters that all embargo. **It
    feeds a live-facing surface**: `lab.run_optimize` is reachable from `valuation/web/app.py:1030`,
    so an inflated out-of-sample IC drove an "Adopt" verdict on a web endpoint. One fold-adjacent
    date is now purged from every training set. **THE ADOPT BOOLEAN IS DELIBERATELY UNCHANGED** —
    the gate has no SE, but **no calibrated floor exists for a walk-forward IC difference and
    inventing one is the error this record warns about most**, so the margin and its SE ship as
    reported fields and changing what adopts is left to an item that can register a bar first.
  * **`MA42` — CONFIRMED LIVE, NOT LATENT, AND THE ZERO IS NOW ATTRIBUTABLE.** The pair IS open
    (vintage 4 shadowing vintage 3, opened 2026-08-13); `months_paired` read 0 on every call and
    the verdict branch was **unreachable**. The repair separates `months_elapsed` (derived, rises —
    1 on 2026-09-13, 6 on 2027-02-13) from `months_paired`, **which is still 0 for a different and
    stated reason: nothing in this repository writes a shadow monthly series at all.**
    `paired_months_owed` makes that gap dated rather than discovered years later — `track_meter`'s
    not-yet-due-versus-due-and-missing distinction applied to the machinery that borrowed its lesson.
  * **`MA43` — THE NO-SYMPTOM CASE, DEMONSTRATED RATHER THAN ARGUED.** `paired_diff` paired by
    POSITION under a docstring promising *"the SAME periods"*. **Two 23-element series each missing
    a DIFFERENT date — equal lengths, so truncation does nothing and nothing raises — give
    −0.0226 positionally against −0.0122 date-keyed.** Now keys on the date intersection and
    **refuses rather than truncates**; both `x3_ablation_rerun.py` call sites pass dates, so the fix
    is not inert, and it is proved inert where inputs were already aligned. **A defect in my own
    fix, found by its own fixture: duplicate dates would have silently kept the LAST occurrence.**
  * **`MA47` — THE B12 COLLISION RE-ENCODED, AND THE DOCSTRING WAS A LIVE FALSE GUARANTEE.** The
    key stored a ticker COUNT for ticker identity. All three panel-shaping env toggles verified
    **in the tree** rather than taken from the audit's list. Replaced by a provenance hash plus a
    **sidecar the read path compares**, so a cache miss can say *why* and a legacy file is refused
    and rebuilt. **An honest limit stated in the code: the vintage is (name, size, mtime), not a
    content hash**, so a byte-identical re-copy reads as new — a spurious rebuild, the safe
    direction. Latent: zero in-tree callers.
  * **A DEFECT IN MY OWN MAP REGENERATION, CAUGHT BY DIFFING THE ARTIFACT.** Repointing the import
    graph at the moved path **silently dropped 187 lines and 22 collisions**, because the audit's
    items still name the old path and the two stopped matching. Fixed with a `MOVED` alias table;
    **the audit's items file is deliberately NOT edited**, since rewriting its paths would make the
    record agree with the tree by fiat. Verified: **285 collisions before, 285 after.**
  * **AND THE MAP WAS BUILT ON A GRAPH `MA60` HAD ALREADY MEASURED TO BE WRONG — FIXED HERE
    BECAUSE REGENERATING IT MADE IT MY PROBLEM.** `MA59`+`MA60` landed mid-session and replaced
    `check_lanes.py`'s hand-typed import dict with a derived graph, having measured the literal at
    **13 keys / 40 edges against a real 118 / 546, 12 of the 13 keys wrong**.
    **`scripts/ma_dependency_map.py` still carried the identical copy** — verified against
    `408e614^:check_lanes.py`, so one graph duplicated, not two of the same size — under a comment
    claiming it was not re-derived because *"a second, drifting copy of an import graph is worse
    than one shared one."* It was the second copy and it had drifted. Now
    `IMPORTS = import_graph.graph()`. **Measured on the 60-item MA set: 285 → 422 collisions, 192
    added and 55 removed** — the map had been calling 192 genuinely-coupled pairs safe to
    parallelise. **Credit is MA60's; this is the copy their change did not reach.**
  * **A COLLISION THE MERGE ITSELF PRODUCED, AND THEIR GUARD CAUGHT IT.** `MA59` archived six of
    the twelve modules `MA23` moved, banner-in-place, the same day. The merge was clean and
    `tests/test_ma59_quarantine.py` then failed six ways **correctly** — its own rule is *"A
    renamed file must not silently empty either list."* The six paths are repointed **in the same
    commit so the diff shows it**, which is what that guard exists to force; the quarantine is
    otherwise untouched.
  * **A SECOND MERGE COLLISION, AND IT IS THE ONE WORTH READING — TWO BRANCHES TOUCHED DIFFERENT
    FILES, GIT MERGED THEM CLEANLY, AND THE RESULT DID NOT IMPORT (2026-08-16).** The options lane
    landed `valuation/edge/parity_flow.py` (`MA31`/`MA32`) on 2026-08-15 importing
    `.surface_stock` — which `MA23` moved to `valuation/studies/` the same day. **No file was
    edited by both sides, so there was no conflict to resolve and nothing to review**; the break
    surfaced only as one suite's `ModuleNotFoundError`. **`parity_flow` FOLLOWED it into
    `studies/` rather than being repointed**, because repointing would have made an ENGINE module
    import a STUDY — the one thing the boundary test forbids — so the fix would have required
    weakening the guard to admit what it exists to catch. **It qualifies on MA23's own criterion,
    verified by census: its only importers are its own `scripts/` runner and its own test.**
  * **AND MY OWN STALE-PATH GUARD WAS BLIND TO THE FORM THE COLLISION ACTUALLY USED.** It grepped
    for the dotted string `valuation.edge.<study>`, which **never appears** in
    `from valuation.edge import surface_stock` — so it stayed **green over three live stale
    imports** while a suite failed at import time. It now reads imports through the **AST** as
    well, and the AST half is **proved non-vacuous by reintroducing one of the three real sites
    and watching it fail** (`('scripts/ma31_ma32_measure.py', 'valuation.edge.surface_stock',
    'ast')`), not by assertion. **A guard that cannot see the syntax the codebase actually writes
    is not measuring the tree** — the same sentence as the comment-vs-code defect two bullets up,
    on the same test, found twice by two different accidents.
  * **PINNED AT M3's STANDARD: 22 of 23 fixtures fail against the pre-fix tree**, measured by
    restoring the sources to `HEAD`. **The one that passes is reported as passing, deliberately** —
    it passes **VACUOUSLY**, because pre-fix neither block was registered and the guard had nothing
    to look at, which is exactly the blindness MA40 closes. **REPORTED OUTSIDE THIS LANE
    (`RUN_RULES` rule 3): two `POST` endpoints under `/api/edge/` in `valuation/web/app.py` carry
    no auth decorator and there is no `before_request` guard on that prefix** — MA7's class, app
    lane's to fix, and it was NOT established here whether that blueprint is mounted in the
    deployed image. **99 suites, 0 failures; 31 new tests** — measured after merging the
    concurrent `MA31`/`MA32`/`MA56` landing, which is why the count is not the 96 this batch
    measured before the merge. `HANDOFF_edge_audit.md` MA23+MA40-43+MA47.
- **THE PROJECT HAD FOUR HARVEY-LIU-ZHU BARS, NOT THE TWO THE AUDIT FOUND, AND THE "3.0" IS NOT A
  BAR AT ALL — IT IS √(2·ln N) FROZEN AT N = 90, A VALUE THIS PROJECT PASSED ON 2026-08-06
  (2026-08-15, `MA5`+`MA6`).** **Zero trials, `FIXED`-class** — two correctness repairs with no
  hypothesis, no threshold and no verdict, so **equity `N` stays 224** and infra 15, `by_domain` is
  bit-identical across the log append (which is also the check that MA13's stamp still holds), and
  **no published claim moves.** `BACKTEST_RESULTS.json` needs no re-run.
  * **`MA5` — THE SHIPPED PACKAGE CARRIED THE SAME IDEA FOUR TIMES:** `statistics.hlz_significant`
    (the **CONSTANT** `|t| > 3.0`), `fundamental_panel._trials_haircut`, the inline `hurdle` in its
    `multiple_testing` block, and `ablation.py`'s own copy — **and only `_trials_haircut` saw M1's
    floor.** B7's defect class with a *moving* target. One definition now: `statistics.hlz_hurdle`,
    every shipped site delegating, and a test that fails if a second √(2·ln N) appears anywhere in
    `valuation/`. **`hlz_significant` now REQUIRES `n_trials` with NO default** — a default is
    exactly how it froze, and defaulting to the live log would make a pure-arithmetic primitive
    read a file from disk.
  * **THE STALENESS RUNS IN THE FLATTERING DIRECTION, WHICH IS WHY IT MATTERS: the hurdle only
    ever RISES with trials, so a frozen constant can only ever be too EASY.** The two crossed when
    X3 took equity `N` 84 → 104. Today the honest bar is **3.2899** against a constant of 3.0, so
    **anything in [3.0, 3.2899] is "significant" under the constant and is not under the real
    bar.** Nothing sits there today — a latent defect closed before it had a second caller.
  * **WHICH PUBLISHED COMPARISONS MOVE: NONE — CHECKED, NOT ASSERTED.** The headline long-short HAC
    *t* **2.6199** fails both. **X2's "clears 3.0 on three of the seven" holds at EVERY `N` the
    project has ever run** (2.9768 / 3.0 / 3.0478 / 3.0834 / 3.2899), because every candidate
    hurdle lands in the empty gap between the 4th and 5th grids (**2.926 and 3.374**) — **by luck
    of where the draws sat, not by design.** It first becomes four-of-seven-fail at equity
    **`N` > 296.5**, ~70 trials out. Session 12's placebo-floor warning in a second costume.
  * **A NEAR-MISS THE SWEEP CAUGHT AND THE AUDIT NEVER NAMED: `param_search.py` computes Hansen's
    SPA recentring √(2·ln ln T)** — the law of the ITERATED logarithm over **sample length**, not a
    trial count. **Consolidating it would have silently changed the SPA test.** It is excluded by
    **structure** (its log argument is itself a log), never by filename. **The refactor is
    bit-identical**: max |Δ| **0.000e+00** over 2,010 values, and `_trials_haircut(8)` still returns
    exactly 3.2898772171176964 — the literal MA13 pins, so no stamp edit was needed.
  * **`MA6` — THE TRIAL COUNTER'S ONE PATH ROUTED TOWARD A *SMALLER* `N`.** `by_domain[dom] += k`
    ran only when a domain resolved, so a row with a typo'd or blank domain cell was added to
    `trials` and to **no bucket** — and `trial_count(domain=...)` reads the bucket. **A real search
    charged to nobody**, while every other degradation here is routed toward a LARGER `N` and
    reported. **M1's own stated error, inside M1's own parser, for the second time.** Unresolved
    rows are now **charged to every family** (they cannot be attributed, and overstating `N` is the
    safe direction), named in `rows_domain_unresolved`, and `sum(by_domain) + unresolved == trials`
    ships as a checkable boolean.
  * **DOES `N` MOVE? NO — 0 unresolved rows measured, so the DSR bar and the HLZ hurdle are
    unchanged and no claim needed re-checking.** The defect is **latent**; the fix changes what the
    **next** typo'd domain cell costs, and a test asserts the zero so a future one shows up as a
    deliberate change rather than a silent one.
  * **THE AUDIT'S SECOND HAZARD IS CLOSED REPORTED-ONLY, AND HALF OF IT DELIBERATELY IS NOT.**
    **Both log tables are NINE columns wide with different orders**, so the width guard cannot see a
    row filed under the wrong header. `rows_misfiled_table` catches the direction with a
    zero-false-positive rule (a verdict cell of the exact form `n=<k>` cannot be a verdict) and
    reads empty. **The reverse direction is NOT detected** — it would need a vocabulary of verdict
    words, i.e. a second definition of "verdict" that would cry wolf on the first new one.
  * **TWO DEFECTS IN MY OWN GUARD, BOTH FOUND BY RUNNING IT:** the source sweep fired on **its own
    documentation** twice (it now strips comments and strings with `tokenize` — *a guard that
    cannot tell code from prose about code is not measuring the tree*), and a docstring of mine
    claimed a fixture passed pre-fix when restoring the sources showed it errors. **11 fixtures,
    all 11 failing against the pre-fix tree.** A status correction too: both rows read
    `IN PROGRESS (app fixer)` and **neither was ever in flight** — the same id collision the ledger
    already documents two rows away, in `MA9`/`MA10`. `HANDOFF_edge_audit.md` MA5+MA6.
- **FOUR OPTIONS CORRECTNESS REPAIRS, AND IN THREE OF THEM THE AUDIT'S OWN MAGNITUDE WAS EITHER
  UNMEASURED OR THE WRONG QUANTITY (2026-08-15, `MA44`+`MA45`+`MA46`+`MA48`).** The master audit's
  wave-2 options-bot batch, taken together because their **eight files do not overlap at all**.
  **Zero trials, all four `FIXED`-class** — no hypothesis, no threshold, no verdict against a bar —
  so options `N` stays **292** and no published claim moves.
  * **`MA44` — THE DOCSTRING WAS FALSE, AND IT IS FOUR SITES AND TWO RULES, NOT TWO AND ONE.** No
    date filter: `intraday/providers.py:168` (Tradier) and `:282` (yfinance, which the audit does
    not name). Strictly after `as_of`: `chain_summary` **and** `options_live.term_read:273-274`.
    **So the odd one out is the LIVE SUMMARY, not the reconstruction, and the live scan's own two
    legs can disagree with EACH OTHER on a 0DTE day** — volume, OI and `atm_iv` from the dying
    chain while `term_slope` comes from the next expiry. The strictly-after rule is also the one
    the term threshold was **fitted** on.
  * **MEASURED, where the audit's verification was "log one Friday scan": 19,825 cached chain-days
    across 39 names. 12.46% list a same-day expiry beside a future one — 60.2% of FRIDAYS, 1.5% of
    Thursdays, 0.0% Monday to Wednesday, 39 of 39 names** — and **the 0.5 volume-vs-OI bar (MA38's
    bonus) is crossed by ONE SIDE ONLY on 23.14% of them**, ~2.9% of all chain-days. **NOTHING
    MOVED**: whether Tradier lists today on an expiry day is a live vendor behaviour this repo
    cannot observe, so matching a rule that might not hold could **break** parity rather than fix
    it. The false claim is gone, `include_expiring` names the other rule (default bit-identical),
    and all three paths now REPORT the expiry used. **Parity is ROUTED, not taken.**
  * **`MA45` — THE ROW-LEVEL NUMBER IS THE WRONG NUMBER, WHICH IS MA38's LESSON AGAIN.**
    `enrich_chain` solved IV from `(bid+ask)/2` with no validity test while `options_greeks` has
    always refused those rows, and the unvalidated path is the **LIVE** one (`term_read →
    _atm_iv_bs → enrich_chain`). **26.08% of 4.35M cached rows are one-sided (0.00% crossed) — but
    the ATM row the walk LANDS on is one only 0.44% of chain-days.** When it bites it is severe and
    one-directional: **front IV moves a median +0.1262 (12.6 vol points) against a 0.0105
    threshold**, the bar flips on **0.29%** of chain-days, and **5 of 6 flips are alerts that pass
    today and would fail** — the audit's direction confirmed. Fixed by **one shared
    `usable_quote`**, deliberately EXACTLY the greeks rule and no selection criteria; **the row is
    KEPT and its `iv` goes NaN** rather than dropped, so no caller's row count moves, and
    `pick_contract` is **bit-identical** because `quote_reject_reason` already refused those rows
    after enrichment.
  * **`MA46` — MY FIRST FIX WAS WRONG AND THE COLLISION IS THE USEFUL PART.** B15 made the
    backtest's `return_pct` net; the tracker still computed the quantity B15 had renamed. Netting
    the tracker's headline — the audit's first option — **collides with MA36: a worthless expiry
    must read EXACTLY −100% and netting makes it −100.26%**, and **an expiring option is never
    SOLD, so there is no second commission leg to charge at all.** **Four suites caught it, and
    they were right, not stale** — the temptation to read four red suites as four outdated
    expectations is exactly how a correct convention gets edited away. Shipped the audit's
    **second** option instead: **record both**, `expectancy_pct_net` beside `expectancy_pct` with
    `pnl_basis` naming which is which. **No published figure moves — proved by those four suites
    going green again with NO edit to their expectations.**
  * **`MA48` — CONFIRMED IN CODE, MEASURED LATENT, AND MY OWN SHARPER HYPOTHESIS REFUTED.** A year
    mined while still current is right-truncated and `needs_pull` only ever compared **DEPTH**, so
    it is cached forever. I expected past years to be silently truncated too, since the evidence
    disappears once the calendar rolls over. **Measured: 0 of 5,063 cached symbol-years were mined
    during their own year** — verified against the frames' own `max(date)`, 14 of 14 running Jan 2
    → Dec 31 — **and there are zero 2026 files.** So **no banked study is affected and the repair
    re-mines nothing.** A `.span` sidecar plus one shared clamp closes it; a legacy file counts as
    complete for a PAST year on the strength of that measurement, and stale for the current one.
  * **REPORTED OUTSIDE THIS LANE (`RUN_RULES` rule 3): `options_fill.round_trip` charges TWO
    commission legs even when it settles at intrinsic** — a worthless expiry is never sold, so the
    backtest is slightly too harsh on exactly the −100% tail MA36 restored. Pre-existing, on the
    banked books, and correcting it would move published figures. Also still open from MA38: both
    live producers turn a missing open interest into a **zero COUNT**, and `providers.py:190-191`
    does the same for VOLUME.
  * **NOT TAKEN, and the brief is corrected: `MA31` is WAVE 3, not wave 2.** It is the
    Cremers-Weinbaum matched-strike parity deviation — **the largest un-run item either audit
    named** — a real research arm that **charges trials** and needs its own blind pre-registration.
    Running it inside a correctness batch is precisely what the register exists to prevent. **It is
    the recommended next item and wants a session of its own.** **87 suites, 0 failures; 34 new
    tests, 27 of which fail against the pre-fix sources.** `scripts/ma44_ma45_ma48_measure.py`,
    `data/free_analysis/MA44_45_48.json`; `HANDOFF_optionsbot.md` §60.
- **A BROKEN BACKTEST COULD SHIP A CANONICAL RESULTS FILE THAT ACTIVELY CLAIMED TO BE HEALTHY —
  THE DEGRADED-RUN DETECTOR WATCHED 6 OF 13 BLOCKS, AND THE RUN'S OWN ERROR REPORT WAS BUILT AND
  THROWN AWAY (2026-08-15, `MA39`).** **Zero trials, `FIXED`-class** — a correctness repair with no
  hypothesis, no threshold and no verdict, so **equity `N` stays 224 and infra 15**, `by_domain` is
  bit-identical across the log append (which is also the check that MA13's stamp still holds), and
  **no published claim moves.** `BACKTEST_RESULTS.json` needs no re-run.
  * **THE UNWATCHED SEVEN, MEASURED ONE FIXTURE PER BLOCK BEFORE ANY FIX: `factors_used`,
    `holdout_validation`, `costs`, `book_configs`, `no_trade_band`, `after_tax`, `benchmarks`.**
    B22 stamps an error status onto all **thirteen** `RESULT_BLOCKS`; `results_file`'s scan iterated
    a hand-typed **six**. An exception inside any of the seven shipped `errors: []` and **no DEGRADED
    banner** — seven for seven. **An empty `errors` is not an absence of information:** the file's own
    contract, in the comment above the field, is *"Non-empty means the run is DEGRADED"*, so a broken
    run was **asserting it was fine** in the file this project uses as its memory.
  * **THE DEFECT WAS TWO LISTS, NOT A SHORT ONE, AND THAT IS THE PORTABLE PART.** `RESULT_BLOCKS`
    lived in the module that **produces** the blocks; the module that **scans** them could not import
    it without a heavyweight cycle, so it grew a copy — and B22 later added `benchmarks` to one of
    them only. One definition now sits in `payload_schema` (imported by both, depends on nothing) and
    `fundamental_panel.RESULT_BLOCKS` is a **re-export**, so every existing importer is unaffected;
    a test pins object identity **and** that exactly one literal assignment exists in the tree.
  * **THE AUDIT'S OWN SUGGESTED FIX BREAKS EVERY HEALTHY RUN, verified rather than argued.**
    *"Iterate all of `RESULT_BLOCKS`"* taken literally raises `AttributeError: 'list' object has no
    attribute 'get'` **ON SUCCESS**, because `factors_used` is a LIST of theme names — a 20–40 minute
    run would have lost its results file to it. Proved by monkeypatching the naive scan in and running
    the healthy fixture against it, and pinned by the refusal-direction test.
  * **THE SECOND HALF: `build_payload` rebuilt `errors` from scratch and never read `res["errors"]`**
    — which carries B22's `"INCOMPLETE RUN"` report, **the only signal that a block went MISSING
    rather than raised**, and the original exception's type and message. Both are plain **strings**
    where the payload holds **dicts**, which is how they came to be dropped for being the wrong shape.
    **A guard whose finding is discarded on the way to the record is not a guard.**
  * **FIXTURES AT M3's STANDARD: 3 of 4 FAIL against the pre-fix code**, measured by restoring the
    three sources to `HEAD`. **The fourth is reported as passing pre-fix, deliberately** — it is the
    refusal direction, its known-bad input is the *naive fix*, and four green "known-bad" fixtures
    would be a lie.
  * **THE CENSUS, AND IT LEAVES ONE ROW OPEN: `payload_schema.BLOCK_SPEC` guards 7 of the 22
    dict-valued payload blocks** — same disease, **`MA40`'s row, deliberately NOT fixed here** because
    it carries a real decision (register the blocks, or drop the computation). **A correction to the
    audit in passing: it estimates "7 of ~17"; measured against the real artifact it is 7 of 22.**
    Also **reported not fixed**: `missing_result_blocks` has exactly **one** caller, so a path
    reaching `results_file.write()` directly gets no missing-block check — left open because
    `build_payload` has many legitimately partial callers and the check would cry wolf on all of them.
  * **WHAT IT DOES NOT SAY: no existing result changes.** The shipped artifact carries `errors: []`
    from a run in which nothing raised, so this **retracts nothing** — it changes what the **next**
    broken run will say. **81 suites, 0 failures.** `HANDOFF_edge_audit.md` MA39.
- **AN ALERT BONUS DIVIDED A WHOLE-CHAIN NUMERATOR BY A PARTIAL DENOMINATOR — AND BOTH FIXES THE
  AUDIT PROPOSED ARE 19× AND 37× MORE DISRUPTIVE THAN THE DEFECT THEY REPAIR (2026-08-15,
  `MA38`).** **Zero trials, `FIXED`-class** — no hypothesis, no threshold, no verdict against a
  bar, so no register (the `S25`/`PT-WRITER` precedent). Options `N` stays **292**;
  `rows_fixed_not_counted` **32 → 33**, which is the proof the row was seen and correctly excluded.
  * **THE PREMISE IS CONFIRMED EXACTLY.** `chain_summary` sums `call_volume` over **every**
    contract in the front expiry and `call_oi` over **only** those whose open interest is known
    (B4 made it exclude the `-1` the cache writes when the OI call failed, which was right).
    `options_signals` then forms `call_volume / call_oi > 0.5` for its **+8 "Unusual call volume
    vs OI"** bonus. `grep known_frac` across the repository finds **ONE producer and ZERO
    readers** — the disclosure B4 shipped to catch exactly this was never wired to anything.
  * **THE DECIDING FACT IS ONE NEITHER THE AUDIT NOR THE LEDGER ROW STATES, AND IT IS THE MOST
    PORTABLE THING HERE.** The audit's 11.4% is a share of cache **ROWS**, which cannot settle
    whether the defect fires: if missing OI were **all-or-nothing** then `coi` would be either
    right or exactly **0**, the shipped `coi > 0` guard would already block the bonus, and the
    correct action would have been to **retire** the field. Measured over **41,321 front-expiry
    chain-days across 41 cached symbols: 75.2% fully covered, 0.09% empty, 24.87% PARTIAL.** It
    is live. **A row-level coverage statistic cannot answer a per-day question.**
  * **THE BLAST RADIUS IS SMALL AND ONE-DIRECTIONAL, and the second half is what makes the first
    usable.** **27 days (0.065%)** cross the 0.5 bar for no reason but the mismatch, and **ZERO
    cross the other way** — so the defect could only ever have **ADDED** an alert, never hidden
    one. That bounds what it can have done to the banked books **without re-running them**.
  * **BOTH OF THE AUDIT'S PROPOSED FIXES COST MORE THAN THE DEFECT, MEASURED AGAINST THE SAME 27
    DAYS.** Scaling `coi` by `1/known_frac` kills **501** otherwise-legitimate fires (**18.6×**);
    suppressing the bonus below **0.9** coverage kills **1,005** (**37.2×**). **The mechanism is
    measured rather than argued: volume is CONCENTRATED in the known-OI rows (median +0.50 excess
    share of volume over share of rows)**, so imputing **average** OI onto rows carrying far
    **below-average** volume inflates the denominator against a numerator those rows barely feed.
    A 0.9 floor is also an **uncalibrated bar**, the error this record warns about most often.
  * **SHIPPED INSTEAD, AND IT IS NEITHER OF THE TWO: take both sums over the SAME rows.** New
    `call_volume_oi_known` / `put_volume_oi_known`. It **imputes nothing, introduces no constant,
    and at full coverage is a bit-exact no-op.** `call_volume` stays whole-chain because the
    put/call ratio wants it that way — **only OI goes missing, not volume.**
  * **AN HONEST LIMIT ON THAT CHOICE, stated in the artifact and the script rather than left to be
    noticed: the matched construction is the REFERENCE the other two are scored against, so "it
    has no collateral" is TRUE BY CONSTRUCTION and is not evidence for it.** The case for it is a
    priori plus the independent concentration measurement.
  * **THE LIVE PATH IS BIT-IDENTICAL, WHICH IS THE POINT OF THE SCOPE.** Tradier ships no coverage
    figure, so the consumer falls back to the old numerator and **no live alert changes** — pinned
    by test. Changing which alerts the live engine fires is a **construction change, not a bug
    fix.** The fraction is now **wired rather than retired**: it reaches `detail` beside a new
    `oi_ratio_basis` naming which numerator was used.
  * **NOT DONE, named so it is not mistaken for done: the banked 22b/R2 books are NOT re-run** and
    were built under the defect; the one-directional result bounds the direction, not the size.
    **REPORTED, OUTSIDE THIS LANE (`RUN_RULES` rule 3): BOTH live producers turn a missing open
    interest into a zero COUNT rather than an unknown** — `providers.py:192-193`
    (`... or 0`) and `:286-287` (`openInterest.fillna(0)`) — **the same defect class, and unlike
    the cache neither ships a coverage figure to detect it with.** `tests/test_ma38_oi_coverage.py` 9/9, **4/4 mutations caught** including one that
    adds the audit's own 0.9 bar; `scripts/ma38_coverage.py`,
    `data/free_analysis/MA38_OI_COVERAGE.json`; `HANDOFF_optionsbot.md` §59.
- **THE LIVE OPTIONS RECORD WAS CENSORED AT ONE END AND BLENDED AT THE OTHER — A WORTHLESS
  EXPIRY WAS STRANDED OPEN FOREVER, AND A TUNING LOOP WAS LEARNING FROM AN ERA THE PROJECT HAD
  FORMALLY RETIRED (2026-08-14, `MA36`+`MA37`).** `PREREG_ma36_ma37_record_integrity.md` committed
  **ALONE at `53c7ecf`**, a strict ancestor of every behaviour change. **ZERO TRIALS, `FIXED`-class
  — and the register exists anyway, because both items MOVE A PUBLISHED NUMBER and MA37 required
  choosing WHICH ERA USERS SEE, which is not a choice to make after seeing which era flatters.**
  * **`MA36` — THE CENSORING IS ONE-SIDED, WHICH IS WHY IT MATTERS.** `_exit_decision` returns
    `"expiry"` from `CLOSE_BEFORE_EXPIRY_DAYS` out and never stops; the B5-lesser no-bid branch
    defers. Past expiry those compose into a **permanent** defer, and `_stats`/`paper_report` count
    `status='closed'` only — so the position is not a loser, it is **ABSENT**. A long option that
    decays to no bid IS the total loss, so **winners and quoted losers were scored and the
    −100% tail was dropped**, in the project's #1 remaining validation, and in the exact opposite
    direction to the backtest it exists to validate (*"expire worthless settle at intrinsic and
    post −100%. They are not dropped."*). `grep -c intrinsic paper_track.py` → **0**.
  * **THE SETTLEMENT PRICE IS ZERO AND IS NEVER RECONSTRUCTED — THE MOST PORTABLE THING HERE.** A
    non-zero intrinsic needs the underlying **at expiry**, and `TradierProvider.get_bars` returns
    close/high/low/volume lists and **drops the dates**. Using *today's* underlying instead books a
    **fake gain on a dead call** whenever the stock rallied after expiry — `V6-OPT`'s settlement
    trap in a new costume, **with its error running in the FLATTERING direction**. An
    in-the-money guard blocks rather than guesses, and it can only ever **prevent** an automatic
    −100%, so it cannot manufacture a loss. **B5-lesser is NOT reversed:** before expiry a no-bid
    position still defers, and the test is **strictly** `today > expiry`.
  * **THE RESTATEMENT IS DATED AND KEEPS THE FIGURE IT REPLACED.** Settling the tail restates a
    published number, and a restatement keeping no record of what it replaced is indistinguishable
    from the figure having always been that — so `scream_log`'s archive convention (nothing
    removed, everything dated) is applied to the **statistic**. A cycle that settles nothing writes
    nothing. **The stranded rows are on Render, not here: the first real restatement happens on the
    next live cycle** and will show in `options_summary().restatements`.
  * **`MA37` — `record_epoch` WAS WRITTEN ON EVERY ROW AND READ AS A FILTER BY ONE MODULE:** 17
    occurrences in `scream_log.py`, **2** in `options_tracker.py` (the field entry and the stamp),
    **0** in `options_paper.py`. So `scorecard`, `tuning_candidates` and `paper_report` all blended
    the era retired on 2026-08-13 for *"predating the corrected alert stack (B1 price basis,
    C-series fixes)"*. **A tuning loop proposing which fingerprints to favour on the strength of
    retired rows is the defect that matters, not the display.** Now scoped to the **current epoch**;
    `EPOCH_ALL` restores the blend; every payload carries the per-era census, so the archive is
    **excluded and never invisible**. `live_since` was the most misleading half — a bare
    `min(alert_ts)` dated the live book from the archived era, making it look **older than it is**.
  * **A DEFECT IN MY OWN REPAIR, CAUGHT BY THE TEST WRITTEN TO PIN IT.** The first cut returned a
    bool, so a *blocked* row fell through to the generic defer and **overwrote the note saying why
    it was blocked** — a diagnosis destroyed by the code that produced it. Now tri-state.
  * **A CORRECTION AGAINST MY OWN REGISTER, AND IT IS THE ERROR THIS FILE WARNS ABOUT TWICE.** Its
    section 6 says *"equity at 218, infra at 11"*; measured after this session's merge `by_domain`
    reads **equity 224, options 292, infra 14** — and infra reads **15** after the concurrent `MA19`/`MA13` landing merged in an hour later, which is the same drift one level down and is recorded rather than left to rot. Quoted from a stale mid-session figure instead of
    re-read after merging `origin/main`. The register is left unedited. **`N` did not move**, which
    is the substantive claim and is verified: `by_domain` is identical before and after, while
    `rows_fixed_not_counted` rises **29 → 30** — the proof the row was seen and correctly excluded
    rather than silently dropped.
  * **AUDIT #3's MERGED RECORD IS NOW TRACKED AND INGESTED.**
    `VALQUO_MASTER_AUDIT_ULTIMATE.md` (+ items JSON + PDF) were **untracked**; all three are
    committed byte-identical, and its **60** items (35 Pass A + 25 Pass B — **not 61**) are one
    ledger row each. **Two things a verbatim ingest would have got wrong: `MA18` is HIGH by the
    audit's own Correction 1 and MEDIUM in its JSON** (the audit's #2 action item, under-rated by
    the machine-readable set), and **`MA7` is NOT done though `14c00ac` names it** — that commit
    changed only the audit documents. **And `build_ledger.py` was REFUSING TO RUN AT ALL** on three
    pre-existing rows carrying raw `|` inside cells; `M1-PARSE`, whose own subject is that hazard,
    was one of them. **72 suites, 0 failures; 19 new tests.** `HANDOFF_optionsbot.md` §58.
- **THE CALIBRATED FLOORS ARE RE-DERIVED AT TODAY'S `N` AND FIVE OF SEVEN HAVE NEVER MOVED -
  INCLUDING BOTH LONG-SHORT FLOORS - WHILE THE 1.95pp ALPHA MARGIN TURNS OUT TO HAVE BEEN STALE
  FOR NINE DAYS (2026-08-14, `MA19`+`MA13`).** `PREREG_ma19_ma13_recalibration.md` committed
  **ALONE at `0eb95b1`**, a strict ancestor of every measurement commit. **ZERO equity trials** -
  and the reason is not bookkeeping: **`N` is the INPUT to the floors being computed, so charging a
  trial would move `N` to 225 and invalidate the numbers the moment they were written.** Equity `N`
  stays **224**; infra 14 -> 15 on the `HACFLOOR`/`X7RECON` precedent, and infra `N` gates no
  published claim. **The full old-bar-vs-new-bar table is in the X7 CALIBRATED THRESHOLDS bullet
  below, recalibrated in place.**
  * **NO SHIPPED CLAIM CHANGES ITS RELATIONSHIP TO ITS BAR, and both moves are in the strategy's
    favour.** Only two floors moved: **top-decile alpha HAC *t* 2.2913 → 2.0540** and **Deflated
    Sharpe 0.7216 → 0.6637**. The long-short naive (**2.1437**), long-short HAC (**2.2837**), theme
    IC *t* (**2.7072**) and PBO (**19.667%**) floors are **bit-identical at `N` = 84, 129 AND 224**.
  * **MA19's OWN PREDICTION IS REFUTED, AND THE REASON IS THE PORTABLE PART.** It expected the
    long-short floors to FALL, since fewer adopters means fewer noise draws collecting the ~+1.4 *t*
    adoption bonus. **They did not move by a single bit.** A p95 over 100 draws is set by the
    5th-and-6th largest values, so **whether a floor moves depends not on HOW MANY draws flip but on
    WHERE THEY SAT**: the two that flipped ranked **15th and 35th** on the long-short statistics and
    **4th** on the alpha HAC *t* - which is precisely the one that moved. **A calibrated placebo
    floor is a STEP FUNCTION of `N`, and the steps are at the tail.** X7RECON's rule is vindicated
    *as a rule* - you must check - while its predicted *direction* is not a reliable guide.
  * **THIS IS THE FIRST TIME SESSION 12's WARNING ACTUALLY FIRED.** It recorded that the floors
    surviving an `N` change was **"luck, not design"**. On the alpha HAC *t* the luck ran out.
  * **THE UNPREDICTED FINDING: THE RECORD'S 1.95pp ALPHA MARGIN HAS BEEN WRONG SINCE 2026-08-07 AND
    THE CORRECT FIGURE IS 1.863pp.** It is not a discrepancy - the `N` = 84 regime was
    **reconstructed** and reproduces X7's 1.95pp to |Δ| 3.2e-05, so X7 measured it correctly and the
    regime moved. **Session 10's sweep measured the new value, banked it, and published only the
    long-short floors.** `RUN_RULES` rule 9 running backwards: **storing the draws is necessary and
    NOT sufficient - someone has to read them out.** The new bar is LOWER, so the correction is
    permissive and retracts nothing.
  * **THE DEFLATED SHARPE MOVES BY A DIFFERENT CHANNEL, AND SO DOES THE REAL STATISTIC.** `N` enters
    `sr0` in the formula itself, so **every** draw moves, not only flipped ones. **The shipped DSR
    reads 0.7863 at `N` = 224** against 0.8628 at 121 and the 0.8674 the record quotes at 116. **A
    real-vs-floor comparison must be made at ONE `N`** - the record's *"0.8674 vs the 0.7216 floor"*
    pairs an `N` = 116 numerator with an `N` = 84 denominator. **At a consistent `N` = 224: 0.7863 vs
    0.6637 CLEARS; against the 0.95 convention it still FAILS.** Same sentence, now consistent.
  * **THE AUDIT'S METHOD CLAIM IS HALF WRONG, AND THE FAILING HALF IS THE ONE THAT MATTERS.** MA19
    says *"the check is arithmetic, not a sweep"*. The adopt SET at any `N` is arithmetic from the
    banked `(margin, se)` - confirmed, the curve reproduces session 12 exactly. **The FLOORS are
    not: only 1 of the 100 banked rows carries BOTH weight-scorings**, so a flipped draw cannot be
    re-scored from the bank. **Three draws were re-scored** on the same panel checkpoint, seeds and
    estimator - **400 seconds, not 3.4 hours** - and the 98 untouched draws are bit-identical at max
    |Δ| **0.000e+00** rather than assumed so.
  * **ELEVEN CONTROLS, TWO GATING, ALL PASS - AND THE STRONGEST IS EXTERNAL.** C10 pushes the **banked**
    real draw (computed at `N` = 121) to today's `N` by closed form and lands on
    **0.786321334173165** against `BACKTEST_RESULTS.json`'s independently-produced
    **0.786321333966452**, |Δ| **2.07e-10**, `sr0` matching to 15 digits - so the Deflated Sharpe
    channel is the **shipped** arithmetic, not a plausible reimplementation (the B7 defect class).
    C4 re-derived seed 1005 at **1.045357 / 2.127284** against session 12's banked
    **1.0453572947436582 / 2.1272844590282975**, an independent reproduction six days later.
  * **`MA13`: `N` NOW HAS TAMPER-EVIDENCE, AND THE PREMISE WAS CONFIRMED BY READING THE SUITE.**
    `test_edge.py`'s M1 test asserts only **relational** properties, **every one of which still
    passes after an edit dropping `N` from 224 to 9** - and lowering `N` **raises** every DSR- and
    HLZ-gated claim. `tests/test_research_log_integrity.py` pins `by_domain` to a **committed
    literal** in the `test_track_meter` idiom, so a change must be made in the same commit and shows
    in the diff. **It is checked for VACUITY** by tampering a real copy of the log and asserting the
    count falls. **A DEFECT IN MY OWN TEST, reported because it nearly read as a null:** the first
    cut used a fixed column offset, edited the WRONG table's `threshold` cell, and reported
    *"tampering did NOT lower N"* - which looked like evidence the hazard was not real and was
    actually **session 12's fix working**. `RESEARCH_LOG.md` holds **two tables with different
    9-column schemas**; the test now resolves the column **by header name**, as the parser does.
  * **DECLINED, WITH THE REASON:** the audit suggests sourcing the expectation from
    `BACKTEST_RESULTS.json` (they agree exactly today). **Refused** - that artifact is refreshed by a
    20-40 minute backtest while `N` rises the moment a register lands, so it would be red for the
    ordinary interval between the two. *"A gate that cries wolf is one you learn to ignore."* The
    artifact-vs-log cross-check is **`MA21`'s row**, with its own staleness decision.
    `data/free_analysis/MA19_RECALIBRATION.json`; `HANDOFF_edge_audit.md` MA19+MA13.
- **THE WRITER FAILURE IS DATED AND EVIDENCED AT LAST - AND `recording_ok` STILL CANNOT SAY SO,
  FOR THE THIRD READING RUNNING (2026-08-14, `PT-WRITER`).** **Zero trials** - facts about what is
  on disk and what the code reads, no threshold, no verdict (`S25`/`PT-GAPDUE` precedent). Equity
  `N` stays **224**. **`PT-WRITER` STAYS BLOCKED, ROUTED TO COWORK.**
  * **THE CLOCK MOVED UNDER THE PREDICTION FOR THE THIRD TIME, AND THE GATE DATE IN THIS FILE WAS
    WRONG.** Don's adoption of **S14** (no-trade band, width 0.30) closed vintage 3 and opened
    **VINTAGE 4 on 2026-08-13**. So the bound inception is 2026-08-13, **the operational gate is
    2027-02-13 and NOT the 2027-02-11 the record carried**, and the verdict date is 2031-08-13.
    `expected_trading_days` on the open vintage is **0**, `row_awaited` is 2026-08-14 (today, not
    yet due), `assessable_from` is **2026-08-17**. **Three five-year clock resets in four days**;
    Rule 6 is paid in full each time. **The vintage was DERIVED from the register, not quoted** -
    the task, this file and the ledger row all carried the superseded date.
  * **THE GAP IS DATED AND NAMED, AND ONE INSTRUMENT ALONE CAN SEE IT: vintage 3 owed exactly ONE
    trading day, 2026-08-12, and received ZERO.** It then CLOSED on 2026-08-13, so `recording_ok` -
    scoped to the open vintage because the contract scopes the gate that way - reports nothing about
    it. **This is session 28's second defect firing for real rather than hypothetically** (*a vintage
    event silently clears the recording gap*), and `track_meter.recording_history`, built in that
    session for exactly this case, is now the **only** place the failure is visible: v1 VOID 2 of 6,
    v2 0 of 0, **v3 0 of 1**, v4 OPEN 0 of 0. **Without that audit trail this session would have read
    `None` and had nothing to report.**
  * **THE DECISIVE EVIDENCE IS NOT THE METER - IT IS A DATED FAILURE NOTE THE WRITER LANE WROTE
    ITSELF, STRANDED UNPUSHED FOR FOUR DAYS.** Commit **`41d7b12`** on the **shared checkout's local
    `main`**, 2026-08-10 20:06: *"cannot write row - mechanism for daily prices not documented in
    repo … Cannot write today's row without (a) a documented price-fetching mechanism, or (b)
    guessing at a vendor. Per instructions, logging the gap rather than inventing data."* **That is
    the correct behaviour and it is the answer to the row** - the blocker is **a missing documented
    price mechanism**, not a scheduler fault, a crash or a conditional write. It is invisible on
    `origin/main` because it was never pushed, which is the exact stranded-work failure `RUN_RULES`
    Part A rule 1 exists to prevent, **and the reason three sessions hunted for evidence written on
    day one.** **NOT PUSHED BY THIS LANE** - it sits on `main` and pushing `main` by hand is
    forbidden; the sanctioned route is **Don's `sync.bat`**.
  * **THE INNOCENT EXPLANATIONS ARE REFUTED, CHECKED NOT ASSUMED.** The local copy is **not** a stale
    mirror of a healthy remote: `data_export/valquo_index_track.csv`, pulled from the LIVE service by
    the weekly cron at 2026-08-10 21:27, carries the **same two rows**. Nothing in the repo writes the
    file (third independent confirmation; all five referencing files **read**, and `track-backup.yml`
    is a **backup** whose own docstring restores the other way). `data/valquo_track_history.csv` still
    reads mtime **2026-08-07 18:07** - **five further trading days of silence**.
  * **AN HONEST LIMIT: the last AUTHORITATIVE remote read is 2026-08-10 21:27**, because the backup
    cron is weekly (Sunday 06:17 UTC, next **2026-08-16**) and `/admin/export-track` needs a token
    this lane must never print. **So 2026-08-12's absence is confirmed LOCALLY and not yet on the live
    service.** `workflow_dispatch` is enabled, so it can be settled on demand.
  * **THE BOARD IS QUIET, WITH ONE QUALIFICATION.** No `IN PROGRESS` rows (the single string match is
    `B13`, whose cell reads *"NOT IN PROGRESS"* - a negation); **all 57 remote `worktree-*` branches
    are ancestors of `origin/main`**, none unmerged. **The qualification: local `main` is +1, and that
    one commit is `41d7b12` above.** So the board is quiet but **not fully RECORDED**, and the
    stranded commit is the one carrying the answer to the last live row.
  * **WHAT IT DOES NOT SAY:** the row's own test - a dated miss on an **OPEN** vintage, reported by
    `recording_ok` - has still never been reached, a vintage event having intervened on all three
    attempts. **The next honest reading is 2026-08-17**, provided no vintage event lands first, and on
    the last four days' record that proviso is doing real work. `HANDOFF_edge_audit.md` 2026-08-14.
  * **THE MISSING INGREDIENT IS SUPPLIED THE SAME DAY, AND THE ROW STILL STAYS BLOCKED
    (2026-08-14, app-fixer lane).** The blocker the failure note named now exists in the repo:
    **`valuation/screener/index_mark.py::contract_row()`** returns the contract row (Index mark,
    SPY mark, date) for the bound book, with **two doors onto ONE function** so there is nothing
    to drift - `python -m scripts.track_row` (`--csv`, `--append`, `--date`, `--book`) for a
    writer running in the repo, and `GET /admin/track-row` on the existing `X-Admin-Token` for
    one running off-box. Documented in **`PAPER_TRACK_CONTRACT.md` §7.2a**, inside the blocker it
    answers. **AMENDED 2026-08-18: THERE ARE NOW THREE DOORS AND THE `GET` NO LONGER WRITES.**
    Writing moved to **`POST /admin/track-row?append=1`**, which enforces the contract's rules
    in code - append-only, idempotent per day, intraday marks refused with no parameter that
    switches it off - and returns 201 wrote / 200 already recorded / 409 append-only / 422
    refused so an unattended caller can branch on the status alone. `GET ?append=1` returns
    **405** and touches nothing; a side-effecting GET on the one dataset here that cannot be
    re-derived is reachable by a retry, a prefetch or a pasted link. See **§7.2b** and
    `HANDOFF_appfixes.md` session 39. **`PT-WRITER` still does not close.**
    **AMENDED AGAIN 2026-08-18, LATER THE SAME DAY: THERE ARE FOUR DOORS, THE ACTION *DOES*
    CALL THE WRITE DOOR NOW, AND THE REASON THE ROW IS BLOCKED HAS CHANGED.** The sentence
    that used to sit here - *"nothing calls the new door yet"* - was true for a few hours.
    Don's PR #2 (`cb8c86e`) repointed `track-row.yml` at it, it ran at 20:31 UTC,
    authenticated, reached the door, and returned **HTTP 422: `the book file
    /app/data/valquo_track.json is missing or unreadable`** (`121f5c3` pushed the refusal note
    exactly as designed). That is `load_book` working as written, and it settles the question:
    **THE WRITE DOOR WAS NEVER THE BLOCKER - `data/` is gitignored, so the book has never
    shipped with any deploy and exists only on Don's machine. The service has nothing to
    mark.** The fourth door is **`POST /admin/track-seed`** (`index_mark.seed`), which installs
    the book and the recorded history: the book is gated on `valquo_index.conformance` so a
    truncated scan cannot be installed under the contract's name, an upload may **EXTEND** the
    recorded series and may **never** rewrite or truncate it (records compared cell-for-cell
    *and* the disk bytes required to be an exact prefix of the canonicalised upload), and a
    book may **not** be seeded onto an empty series - because the next append would then start
    a fresh series at today's date with a plausible `day_n` and nothing would raise.
    `python -m scripts.seed_track --send` is the one command. **AFTER A SEED THE SERVICE COPY
    IS THE RECORD** and the local files become a stale backup nothing syncs back. See
    **§7.2c** and `HANDOFF_appfixes.md` session 40. **The row is blocked on Don running that
    command**, which is an irreversible write to the bound record and was deliberately not done
    by the lane that built it. **NO NEW VENDOR** - prices come from the shipped `screener/prices.py` (Stooq ->
    yfinance), no key, nothing a fresh deploy lacks. **IT RAN FOR REAL: 2026-08-13, all 86 names
    priced, `valquo_pct` 4.3232 / `spy_pct` 4.8794 / `excess_pp` -0.5562, exit 0** - and it was
    **NOT written** (read-only, no `--append`), so the recorded series still ends 2026-08-06 and
    **that -0.5562pp is NOT a track record and may not be quoted as one.**
    **STALE AS OF 2026-08-18: the recorded series is FOUR rows and ends 2026-08-17** -
    2026-07-31, 2026-08-06, 2026-08-13 and 2026-08-17 - so the two rows after 08-06 were
    written by the Cowork lane by hand. **The 08-13 row reads `4.25 / 4.88 / -0.62` against
    this bullet's own re-derivation of `4.3232 / 4.8794 / -0.5562`**, so the three-source
    disagreement below is live on a recorded row rather than hypothetical. The seed door
    installs **what is recorded**, verbatim, and arbitrates nothing.
    **HOW CLOSELY IT REPRODUCES THE RECORDED ROWS, AND THE TWO LEGS DIFFER: the BENCHMARK leg is
    EXACT** (2026-08-06 `spy_pct` 3.6228 re-derived against a recorded 3.6228, which is what
    confirms the convention - closing prices, cumulative-since-inception, this vendor - since a
    wrong base date would miss by percent rather than by nothing) **and the BOOK leg is NOT**
    (0.7961 against a recorded 0.7760, **+0.0201pp**, all 86 names priced both sides). **So it is
    CLOSE to the recorded series and is NOT the same arithmetic, and it may not be called the
    SOURCE of it** - a correction against this lane's own first draft, which said exactly that.
    Cause **NOT diagnosed**; hypothesis is dividend/adjustment treatment or a different quote
    vendor for the equity leg. **A switch acquires a ~0.02pp seam**, immaterial against the
    contract's own **sigma of 3.9847pp per MONTH** but real and disclosed. The day-1 row is **not
    a usable comparison in either direction** (78 of 86 names priced against a recorded
    `n_priced` of 86); its benchmark leg misses by 0.0297pp and **hypothesis, not a finding,** it
    looks marked from an **intraday** quote - which is what the new close refusal prevents.
    **WHY THE ROW STAYS BLOCKED: this supplies the MECHANISM and schedules NOTHING** - no cron,
    no task, no workflow, and nothing written to the bound series. Scheduling is Cowork's under
    §7.2 and the row should not close until something actually runs. **Zero trials**, equity `N`
    stays **224**. `tests/test_index_mark.py` 23/23, whose required pin is that the emitted row
    reads back through `index_track.load()` unchanged; mutations 11/11 caught, 0 missed, 0
    skipped; full gate 74/74. `HANDOFF_appfixes.md` session 32.
- **THE CATALOGUE IS EXECUTED - EVERY ROW ADJUDICATED. AND THE LAST FOUR ROWS DELIVER THE
  PROJECT'S STRONGEST POSITIVE RESULT AND ITS MOST INSTRUCTIVE REVERT (2026-08-14,
  `X5`+`M4`+`B23`+`S10-ACCT`).** `PREREG_x5_m4_b23_s10acct.md` committed **ALONE at `264cc49`**, a
  strict ancestor of every measurement commit. **No score moved; all four headlines bit-identical
  throughout; not a vintage event.**
  * **X5 - THE HEADLINE SURVIVES ITS OWN BOOTSTRAP, ON THE AUDIT'S OWN RULE.** 200 resamples of the
    2,531-name universe **WITH REPLACEMENT** at full size: top-decile alpha **p05 +0.05610**,
    median +0.07265, p95 +0.08779, **min +0.04672**, against a full-universe +0.07174 - and **200
    OF 200 DRAWS POSITIVE**, the worst of two hundred still earning **+4.67%/yr**. Long-short HAC
    *t* **p05 +1.63296**, median +2.44187, also **200/200**. The audit's rule was *"if the 5th
    percentile of that distribution is positive, the result is strong"*; **it is.**
  * **C2 IS WHAT MAKES THEM BOOTSTRAPS RATHER THAN SUBSAMPLES, AND IT LANDS ON THE THEORY:** mean
    distinct names **0.632511** against **1 − 1/e = 0.632121**. Duplicates are kept as duplicates;
    de-duplicating would have understated the very variance X5 measures.
  * **THE SCOPE LIMIT IS STATED, NOT HIDDEN.** The panel is **not** rebuilt per draw - a build is
    ~20 min, so 200 is **~66 hours**. The resample re-does the **layer-3** standardisation and the
    whole decile sort (because `quantile_backtest` re-standardises within its slice); **layers 1-2
    were computed once across the full universe**. So **this interval is a LOWER BOUND** on total
    name-selection uncertainty. **PBO is declared absent, not dropped.** Read against X1: the
    bootstrap spread **0.05657** is marginally wider than X1's half-universe **0.05505** - two
    independent perturbation axes agreeing closely.
  * **S10-ACCT IS REJECTED, AND ITS MECHANISM ARM REVERSES S10's FIRST HALF.** The 2-of-3 veto
    (Beneish >−1.78, Altman <1.81, top-decile external financing - all **published** thresholds)
    excludes 5.74% of rows and **IMPROVES** alpha **+0.1970pp**, monotonicity **−0.8909 → −0.9758**
    and the long-short *t* - but **FAILS the drawdown leg at −0.1082pp against a >+2.0pp bar**,
    which is the audit's primary criterion.
  * **THE NUMBER THE AUDIT CALLS THE ONE THAT MATTERS MOST: the excluded names crash at 3.04× the
    rate of the names kept** (2.660% vs 0.874%; 174 crashes of 6,542 rows against 939 of 107,403).
    **S10's VALUATION half found the exact opposite** - that screen deleted names crashing at
    **half** the rate of those it kept. **So the accounting flags carry real information about
    individual-name catastrophe and the valuation band did not - and it still cannot move the
    portfolio's drawdown**, because S10's own first half measured that the worst peak-to-trough
    spans **exactly ONE 63-day period on every arm, COVID 2020Q1**. A name-level screen cannot move
    a market-wide quarter.
  * **THE DEVIATION WAS FIXED BEFORE ANY RESULT AND ITS DIRECTION IS NOT NEUTRAL:** NT filings are
    unbuildable, so this is **2-of-THREE**, which makes the veto **NARROWER** - a name flagged by NT
    plus one other would have been excluded under 2-of-4 and is not here. **A null does not close
    the four-flag rule.** A premise correction against the S17/S19 register: **no panel rebuild was
    needed after all**, because the flags are computed from SF1 and joined, so the eight columns
    were **not** added to `_KEEP` and the live footprint is smaller than registered.
  * **M4 - THE HARNESS EXISTS AND HAS BEEN RUN.** Replaying real historical dates through the LIVE
    and BACKTEST paths: **ρ 1.0 on 2026-01-28 (1,843 names) and 0.999999999999999 on 2009-01-15
    (1,471)**, with **max |composite difference| EXACTLY 0.0 on both** and **zero** top-25 changes.
    **Audit B7's fix is confirmed on real data for the first time** - its existing pin compares one
    synthetic frame. **Why it is worth having though it found nothing:** the panel **hard-codes**
    `residual_momentum=False` while the live path **reads CONFIG**, so they agree today only
    because the defaults were changed to match and **nothing structurally holds them together**.
    The harness **raises** below ρ 0.99 and records both CONFIG flags beside the result.
  * **B23 IS REVERTED ON ITS OWN GATE, AND THE REASON IS WORTH MORE THAN THE SPEED WOULD HAVE
    BEEN.** Sharing the 63-day `keep_numbers` panel leaves **every headline bit-identical** but
    moves `cleanups.panel_window` (**horizon 63 → 756**, `calendar_cut_days` 4,659 → 5,352,
    `cross_section_max` 1,954 → 1,768, **64 per-date entries dropped**) and
    `survivorship_mask_coverage` (`tickers_in_frame` 2,710 → 2,409).
  * **THE MECHANISM, WHICH NOBODY HAD DOCUMENTED: BOTH BLOCKS ARE WRITTEN AS A SIDE EFFECT OF
    WHICHEVER PANEL IS BUILT LAST.** The 63-day build ran last, so they described the 63-day panel
    **by accident of ordering**; remove it and they silently describe the **756-day** panel while
    still sitting beside a headline measured at 63 days. **So the audit's "purely a speed issue" is
    WRONG on this codebase - the fourth build is load-bearing for two reported blocks, and removing
    it is a reporting change wearing a speed change's clothes.** **REVERTED, NOT REPAIRED**, because
    the register's rule was *"revert, do not explain"* and fixing the binding then re-applying would
    be exactly the post-hoc rationalisation that rule forbids. **No speed figure is quoted, because
    the change that produced one is not in the tree.** `run_backtest(panel=None)` survives, inert at
    its default, with the revert and both block names in its docstring.
  * **THREE DEFECTS, TWO IN MY OWN NEW CODE.** `beneish_m` treated a **missing** input as **ZERO** -
    an absent `ncfo` became zero operating cash flow, inflating TATA and **manufacturing a
    manipulation flag out of an absent number** - caught by the test written to pin its own
    docstring, and **REPORTED AS INERT** because re-running gives bit-identical flags. M4's CONFIG
    reference was wrong in two places and the worse one was **silently** returning null behind a
    `hasattr` guard. And the `cleanups` order-dependence above.
  * **Equity `N` 220 → 224, infra 12 → 14.** Expectations **5 right, 2 wrong, 1 split** - and both
    misses are the useful kind: the crash-rate reversal, and B23 turning out not to be a speed
    issue at all.
  * **THE CATALOGUE IS EXECUTED - EVERY ROW ADJUDICATED. 194 ledger rows, 192 adjudicated, and the
    2 that remain are blocked on neither analysis nor decision:** **`B13`** on a data field that
    does not exist in the licensed export (`avg_dollar_volume`; the price file carries date and
    close only), and **`PT-WRITER`** on the Cowork lane, since **nothing in this repository writes
    the bound track file**. **THAT IS NOT A CLAIM THE FINDINGS WERE POSITIVE:** the overwhelming
    majority are rejections, nulls and corrections, and that remains the record's central fact.
    `data/free_analysis/X5_BOOTSTRAP.json`, `S10_ACCOUNTING.json`, `M4_LIVE_REPLAY.json`;
    `HANDOFF_edge_audit.md` X5+M4+B23+S10-ACCT.
- **THE HEADLINE SURVIVES A SPLIT BY NAME - AN INDEPENDENCE AXIS IT HAD NEVER BEEN TESTED ON -
  AND IN THE SAME SESSION IT IS FOUND NOT TO CLEAR THE HARVEY-LIU-ZHU HURDLE (2026-08-13,
  `X1`+`R4`).** `PREREG_r4_x1_accounting_and_universe_split.md` committed **ALONE at `9aee4f7`**, a
  strict ancestor of every measurement commit. **No score moved and this is NOT a vintage event** -
  C1 gated the full-universe headline bit-identical before any split was read.
  * **X1 IS THE STRONGEST POSITIVE RESULT THIS PROGRAMME HAS PRODUCED, AND THE AUDIT SAID IT WOULD
    BE THE MOST VALUABLE TEST IN THE DOCUMENT.** Every held-out gate this project has ever run
    splits by **DATES**, which conflates *"does the signal generalise"* with *"does the PERIOD
    generalise"*. A **universe** split has **no regime confound at all**. Splitting the 2,531 names
    into disjoint halves - the audit's own stable key, `sha1(ticker) % 2`, **1266/1265**, no seed,
    reproducible by anyone holding the ticker list - plus **100 seeded random splits**, against a
    null **rebuilt for half books**:
  * **A1 (top-decile alpha) SURVIVES, and emphatically. 200 of 200 half-books clear their own bar;
    100 of 100 splits clear on BOTH sides; the median half-book is +0.07233 against the full
    universe's +0.07174; and ZERO of 400 half-book measurements came back negative.** The minimum
    across 200 half-books is **+0.04382**, nearly three times the null's p95 of +0.01724. **Halving
    the universe widened the error bars and did not move the centre** - which is what a broad,
    uniform cross-sectional effect looks like.
  * **A2 (long-short HAC *t*) SURVIVES BUT DISTINCTLY MORE MARGINALLY, and the pre-registered bars
    are what separate them:** 93.0% of half-books and 86.0% of splits, against A1's 100%/100%. Its
    median half-book *t* **+2.3617** sits BELOW the full-universe **+2.6199**, as a half-sized book
    sorting a noisier spread should, and **14 of 200 half-books fail their own bar. A1 is the
    stronger claim and should be quoted as the stronger one.**
  * **A SCOPE LIMIT FIXED BEFORE THE RUN, AND SAYING IT IS NOT A DODGE.** The audit asks to
    *"decide on half A, measure on half B"*; **that half cannot bind, because the deployed strategy
    fits NOTHING** - flat 1/7, never tuned, `cpcv.adopt` false on every run - **so there is no
    decision to leak** and X1 as run tests **generalisation across NAMES**, not decision leakage.
    **Re-running every theme decision and the weight selection under the split is NOT done** and is
    named so it is not mistaken for done.
  * **A CROSS-CHECK THAT CORROBORATES AN INDEPENDENT MEASUREMENT.** The half-universe null reads
    **ls_hac p95 1.7405**; S22 separately measured the **FULL**-universe fixed-weights null at
    **1.7494**. **Halving the universe moved the null by 0.009 of a *t*** - so the gap to X7's
    **2.2837** is almost entirely the **CPCV selection step**, which S22 already priced at
    **+0.5343**. Both are fixed-weights nulls and X1's arms use fixed weights, so it is the right
    null; two independent routes to the same number is the best evidence available that it is
    calibrated rather than merely computed.
  * **R4 CLOSES `DONE`, AND THE BULLET NOBODY HAD DELIVERED IS THE ONE THAT FAILS.** Of its four
    method bullets M1 shipped two (the log - 121 rows, **521 trials** - and the real `N` into the
    Deflated Sharpe); this session shipped the other two.
  * **BULLET 3: BH ACROSS THE EQUITY FAMILY LEAVES THREE OF FIFTY-THREE - AND THE SET CHANGES WITH
    THE INFERENCE CHOICE.** `fcf_margin` and `gp_on_capital` survive under both; **`fcf_yield` only
    under the plain *t* and `roic` only under the clustered one**, so *"three survive FDR"* is
    weaker than it sounds. **Rejected by BH:** `roic` +2.8172, `neg_issuance` +2.7556, `roe`
    +2.7303, `pead_car` +2.4572 - several of which the record has quoted as individually
    significant against the retired 2.0 convention. **The audit's analogue is the options autopsy's
    126 FEATURES, not log rows** - which matters, because `RESEARCH_LOG.md` has **no p-value
    column**, so BH across the log is **not computable and never was.**
  * **BULLET 4 IS THE FINDING, AND IT REFUTES R4'S OWN PREDICTION. THE HEADLINE DOES NOT CLEAR THE
    HLZ HURDLE:** long-short HAC ***t* 2.6199121240414884** against **√(2·ln 218) =
    3.2816139513322065**, a shortfall of **0.6617** — **and the SHIPPED artifact reads 3.2844 at
    N = 220, because this session's own two X1 trials landed between the register and the refresh.
    Both are right at their own denominator, the verdict is unchanged either way, and the hurdle
    only ever RISES as trials accumulate.** R4 predicted it *"probably clears"*; that 3.52
    was the **pre-B6 void panel**, and `N` went **8 → 218** meanwhile, so **the statistic FELL as
    the hurdle ROSE**. **The haircut was already computed on every run and used by the CPCV adopt
    gate - nothing had ever compared it to the HEADLINE**, and no `harvey`/`hlz`/`hurdle` string
    existed anywhere in the canonical file.
  * **BOTH SIDES SHIP, BECAUSE THE ANSWER IS A TENSION AND NEITHER NUMBER IS "THE" ANSWER.** The
    project **CLEARS** X7's empirically calibrated **2.2837** and **FAILS** the bar derived from
    counting its own trials. The counter-argument was **registered before the run**: **HLZ prices
    the BEST OF N draws, and the deployed composite is not the best of anything** - flat 1/7, never
    tuned, `cpcv.adopt` false - **so the 218 logged trials are overwhelmingly REJECTED ALTERNATIVES
    to it rather than candidates it beat.**
  * **IT SHIPS IN THE CANONICAL RESULTS FILE, NOT A SIDE ARTIFACT** - `multiple_testing`,
    **registered with M6's field-level guard**, no renames and nothing allow-listed, because a
    number that lives only in a study JSON is **exactly the failure R4 exists to end**.
    `statistics.benjamini_hochberg` is the shared definition; **BH already existed THREE times in
    the options lane and consolidating those is theirs to do.**
  * **A DEFECT IN MY OWN WORK, CAUGHT BY THE DOCSTRING I HAD JUST WRITTEN.** The first cut of the
    script carried **its own BH** - a **FOURTH** copy, which is the audit-B7 defect the shared
    definition exists to end, committed in the same change that argued against it. It now
    delegates, and a test pins the identity.
  * **R4's PERMANENT RESIDUAL:** BH across the **LOG** is not computable without inventing
    p-values; and **`research_log.DOMAINS` declares `unified` and it reads ZERO** - every U-series
    item testing explicitly unified equity+options hypotheses was charged to equity or options, so
    there are **three parallel single-lane families and one dead bucket**. **Measured and ROUTED**,
    since deciding it would move every published `N`. **R5's ledger row already leaned on R4's note
    as routing input.**
  * **A CORRECTION TO MY OWN REGISTER:** it said a half universe gives *"~126-name deciles against
    ~253"*; measured, it is **82.3 against 165.1** - I divided the 2,531-name universe by ten where
    the panel carries **~1,650 names per DATE** after coverage. Direction unaffected.
  * **Equity `N` 218 → 220, infra 11 → 12.** Expectations **5 right, 1 wrong, 1 split, 1
    unscorable** - the miss being that I expected at least one of 400 half-books to come back
    negative and **none did**. `data/free_analysis/R4_X1_ACCOUNTING_UNIVERSE.json`;
    `HANDOFF_edge_audit.md` R4+X1.
- **SELLING A 25-DELTA PUT IS SELLING A 25% ASSIGNMENT PROBABILITY *BY CONSTRUCTION*, SO THE
  STRIKE HAS ALREADY SPENT THE RISK EDGE — THE CSP ON HEALTHY DIPS IS REJECTED BY THE ONE CONTROL
  THAT MATTERED, AND THE `U6` "100% CALLS" BLOCKER IS RETRACTED (2026-08-13, `V6-OPT`).**
  `PREREG_v6opt_csp.md` committed **ALONE at `88685c9`** — one `.md`, zero `.py`, a strict
  ancestor of every measurement commit — and it fixed **BOTH stages** before either ran, so
  stage 2 could not be designed on stage 1's numbers. **ADOPTS NOTHING**; no live code path
  changed.
  * **STAGE 1 IS DESCRIPTIVE AND THE GATE OPENED, WHICH IS WHY STAGE 2 IS INTERPRETABLE.** On
    4,855 covered dipped rows: post-dip `atm_iv_30` sits **+17.71%** above the name's **own**
    trailing 252-day median against **+13.29%** for unhealthy dips (**ratio 1.3328**, so the
    market does **NOT** price the `M1` distinction); a real 25-delta 30–45 DTE put pays a median
    **2.550% of strike** over 32 days — **27.73% annualised** — net of the **shipped** fill
    engine at the touch; and the variance risk premium is **+0.0391** vol points (implied 0.430
    against realised 0.389). **The elevation decays away almost entirely inside 30 trading days**
    (−1.72%, −5.64%, −14.42%, **−16.56%** at t+5/10/20/30).
  * **STAGE 2 IS REJECTED, AND IT FAILS *ONLY* ON THE DISCRIMINATOR THE REGISTER NAMED AS
    DECIDING.** The healthy arm clears three of four conditions and is not marginal about it:
    **+1.1342%/trade** on the cash secured, **positive in BOTH halves** (+1.1348, +1.1178), an
    **84.39% win rate**, and it **beats random entry decisively** — pooled **+0.2612%** over five
    seeds, paired name-year sign test **z +7.2506, p 4.15e-13**, 66.96% of 457 cells positive.
    **It fails condition 2: the IDENTICAL trade on UNHEALTHY dips earns MORE (+1.2651%) and beats
    it in BOTH halves.** So the health floors do no work and the trade is **just short vol** —
    which `A3` already rejected at **−7.99%/trade**.
  * **THE MECHANISM IS MEASURED AND IT IS THE MOST PORTABLE THING HERE.** Assignment comes back
    **25.30% healthy against 25.73% unhealthy** — a 0.43pp gap — while the unhealthy name pays
    **2.978% of strike against 2.550%** because its implied vol is higher (0.474 vs 0.424).
    **A delta-targeted rule sets the strike from the name's own volatility, so it neutralises the
    very risk difference the trade was built to exploit.** Deltas are like-for-like (median
    **−0.2638** vs **−0.2658**, DTE 32 vs 31), so this is not a confound. **A risk signal can only
    pay through an option if the MONEYNESS is held fixed, not the DELTA** — and that is a **NEW
    hypothesis** needing its own register, forbidden here by void condition 3.
  * **THE RISK EDGE IS A QUARTER OF ITS HEADLINE WHERE IT CAN ACTUALLY BE TRADED, AND THE REGISTER
    PREDICTED THIS AT 80/20 BEFORE MEASURING IT.** `C5` re-measured `M1` on the covered rows at
    **−2.797pp** (healthy 29.26% vs unhealthy 32.06%) against `V6-B`'s full-panel **−10.84pp** —
    *below* even its megacap quintile's −3.787pp — because options exist on the large end and
    `V6-B` measured the separation **weakest exactly there**. Covered dips carry a median market
    cap of **$17.92bn against $2.17bn**, an **8.26× tilt**. **Any future options result on this
    population must be quoted against −2.797pp, never against −10.84pp.**
  * **A PREMISE FINDING THAT CORRECTS MY OWN PRIOR SESSION — see the `U6` bullet below.** The
    chain cache is **not** 100% calls: **1,288,750 puts against 1,288,751 calls**, zero tickers
    with no puts. The 3,870-of-3,870 measurement was of the **TRADED BOOK** and the inference from
    it was wrong. U6's **coverage** blocker stands and still carries its verdict alone.
  * **THE SETTLEMENT TRAP, CAUGHT BEFORE THE RUN RATHER THAN AFTER.** Strikes are **as-traded**
    while `data/backtest/prices` is split- **and** dividend-adjusted: AAPL's derived `spot` reads
    **300.35 against an adjusted 72.34** on 2020-01-02, and the two differ by >5% on **46.66%** of
    its days. Settling a $300 strike against $72 books a fake ~76% assignment loss **silently**.
    Session 30's rule is applied in **both** directions — the option settles on the as-traded
    `spot`, and only the **STOCK** control uses the adjusted close.
  * **COVERAGE FORBIDS A FULL-PANEL GATE FOR THE FOURTH TIME** (`S18`, `U2`, `U3`, now this):
    **4,855 of 37,982 dipped rows = 12.78%**, over **40 of 69** dates, **28 of the 29 gaps EARLY**,
    halves **20 and 19** after embargoing 2021-01-21.
  * **CONTROLS: C1 reproduces the premise counts and ABORTS otherwise; C2 ZERO point-in-time
    violations over 4,836 events; C3 `skew_25d` equals `iv_put_25d − iv_call_25d` at max abs diff
    0.000e+00 over 902,851 rows — reproducing `U2` on four times the rows, so it is ONE column and
    never two pieces of evidence; C-QUOTE the derived `mid`/`spread_frac` reconstruct the RAW
    chain's own bid to 3.815e-06 over 216,872 rows; C-D the mirror loses 1.5263%, so both sides
    are not profitable.**
  * **TWO DEFECTS IN MY OWN INSTRUMENT, both caught before the verdict and both PROVED inert by
    leaf diff rather than asserted** — the halves split each arm at its own median date instead of
    the register's single embargoed boundary (289 shared leaves, **ZERO moved**, 5 documentation
    leaves added), and stage 1 banked a contract without its `expiration` (re-run: 668 leaves,
    **ZERO moved**). **REPORTED AGAINST THE ARM:** the survivability leg compounds per-trade
    returns **sequentially** rather than simulating a capital-weighted book, so it **overstates**
    drawdown — it passes anyway, so it cannot have produced the verdict — and the absolute levels
    are severe (**−55.52%** for the arm against **−82.56%** for the stock control at cap 10).
  * **NOBODY MAY READ THIS AS EVIDENCE THAT CASH-SECURED PUTS DO NOT WORK.** The register declared
    the asymmetry in advance because the covered sample holds **one** crash, so a decisive REJECT
    was available and a decisive ADOPT was not. **Options `N` 287 → 292; equity untouched BY THIS ITEM (218 after the merge);
    72 suites, 0 failures.** Expectations **4 right, 3 wrong**.
    `data/free_analysis/V6OPT_STAGE1.json`, `V6OPT_STAGE2.json`; `HANDOFF_optionsbot.md` §57.
- **THE 800-NAME-ERA REJECTIONS ARE RE-RUN AT LAST: SIX NULLS - AND A LIVE "ALL WRONG-SIGNED"
  CLAIM IS REFUTED, EVERY SIGN HAVING FLIPPED POSITIVE ON THE CORRECTED UNIVERSE (2026-08-13,
  `R5`+`R6`).** `PREREG_r5_r6_alphabetical_rerun.md` committed **ALONE at `4b9706b`**, a strict
  ancestor of every measurement commit. **SCORES NOTHING and is NOT a vintage event** - C1 gates on
  the composite returning BIT-IDENTICAL and it did.
  * **ALL SIX NULL, AND NOT ONE CLEARS EVEN THE RETIRED 2.0 CONVENTION IN ANY WINDOW.** R5:
    `neg_ret_1m` median IC **+0.00715** (*t* +0.4546), `neg_max_ret` **+0.02634** (+1.1510),
    `neg_idio_vol` **+0.05452** (+1.2105). R6 on 50 covered dates: `sm_conviction` **+0.01597**
    (+1.2786), `sm_holders` **+0.03285** (**+1.6111**), `sm_avg_position` **+0.03240** (+1.3296).
    Bars are each signal's **own** within-date permutation p95 in both halves. **Coverage is
    comfortable everywhere** (R5 99.5-100%, R6 73.8%, floor 30%), so **no arm is a power failure.**
  * **THE HEADLINE IS NOT THE VERDICT: THE LIVE "ALL WRONG-SIGNED" CLAIM IS REFUTED.**
    `settings.py:222-224` and `factors.py:294-296` both recorded the three anomalies at median IC
    **-0.014 / -0.072 / -0.025**, measured on **400 names over 110 rebalances** - **VOID TWICE**,
    under **B12** (alphabetical slice) and under **B6** (the inverted-universe panel). On the
    corrected 2,531-name / 69-date panel **ALL THREE SIGNS ARE POSITIVE**. They remain rejected
    **for being WEAK, not for being BACKWARDS** - and a live comment had been asserting the
    opposite as current evidence. `neg_idio_vol` is the largest at +0.05452 and **+0.09658 on the
    late half** - a big IC by this panel's standards - carried on a *t* of only 1.21 because the
    early half is +0.1726. **Large and unstable, not strong.**
  * **R6's MECHANISM IS A MARKET-CAP SORT, AND IT IS THE REASON RATHER THAN A CAVEAT.** C6 puts the
    three conviction signals at **-0.815, -0.855 and -0.854** against the `size` theme and at
    **+0.777 to +0.833** against each other - so they are close to **ONE** signal and that signal is
    largely market capitalisation, which the panel already scores. **`sm_holders` is the near miss**:
    it clears its own p95 on the full sample (**+1.6111 vs 1.5285**, the only cell in the register to
    clear anything) and then reads **+0.0118** on the early half. **THE SF3 CONVICTION FAMILY IS NOW
    CLOSED** - five of five members measured on the corrected universe with none clearing.
  * **SIX ARMS ARE NOT SIX INDEPENDENT TESTS, AND THE CAVEAT MUST TRAVEL WITH THE COUNT.** By C6's
    own correlations the effective number is **nearer three** - R6's three inter-correlate 0.78-0.83
    and R5's two volatility cousins 0.698. **The SELRULE lesson.** The charge of six is paid in full
    anyway, because understating `N` overstates significance.
  * **THE LIVE `sm_breadth` SWAP SURVIVES ITS OWN VOIDED JUSTIFICATION - and this was the most
    consequential question in the register.** `factors.py:314-316` replaced `inst_breadth` with
    `sm_breadth` in the **LIVE** institutional theme mean on the strength of *"IC t +2.37 vs +1.48
    on 800 large caps"*, a comparison B12 voided: **a live scoring decision resting on a voided
    number.** Re-measured head to head at near-identical coverage (0.7169 vs 0.7185):
    **`sm_breadth` +1.8481 against `inst_breadth` +1.2371 - THE ORDERING HOLDS**, though the gap
    narrowed from 0.89 to **0.61** of a *t* and **neither clears 2.0**. **AND A REFINEMENT OF THE
    LEDGER'S OWN CLAIM: the +1.73 it cites for `sm_breadth` was dated 2026-08-01, THREE DAYS BEFORE
    the B6/B7/B13 corrections landed**, so it was never a corrected-panel figure either and
    **+1.8481 is the first.**
  * **BOTH INPUTS THE LIVE `low_risk` THEME DOES USE ARE WEAKER THAN THE TWO IT REJECTS:**
    `neg_vol` **+0.8873** and `neg_beta` **-0.3937**, against `neg_max_ret` +1.1510 and
    `neg_idio_vol` +1.2105. **The theme carries ZERO weight in the live composite**, which bounds
    the consequence entirely - **but anyone un-zeroing it should read those four numbers first.**
  * **REGISTRATION IS MEASUREMENT, NOT SCORING, AND THAT WAS GATED RATHER THAN ASSERTED.** The six
    were added to `NUMBER_THEME` (the S2 `cash_op_prof` pattern, `NUMBERS_ALL` 47 -> 53) so they
    acquire a `z_` column, a coverage entry and a per-signal IC row. Every theme mean is an
    **explicit column list**, checked in the code first; **C1 then tested EXACT equality** on
    `long_short_tstat` **2.8360640685320595** and three more headlines. **A tolerance would have let
    a real scoring change through.**
  * **FOUR STALE COMMENT SITES CORRECTED IN PLACE, AND THE DECISIONS UNTOUCHED.** The `sm_breadth`
    swap is **ROUTED, not made** - changing a theme input is a construction change and a vintage
    event. **C7 NOT TRIGGERED and reported as not-run rather than skipped** (neither volatility
    cousin replicated, so R5's own earlier size-interaction clause never fired).
  * **Equity `N` 212 -> 218**, haircut 3.2731 -> 3.2816, **under 0.009 of a *t*** - the ledger's own
    "trial cost is now negligible" argument confirmed at today's `N`. Expectations **6 right, 2
    wrong**; the informative miss is that I priced a better-than-even chance the "wrong-signed"
    finding would survive the universe correction, and **all three signs flipped**.
    `data/free_analysis/R5_R6_ALPHABETICAL.json`; `HANDOFF_edge_audit.md` R5+R6 sections 0-9.
- **THE DIP BRANCH LIVES: A HEALTHY 20% DRAWDOWN FALLS A FURTHER 20% A QUARTER LESS OFTEN, AND IT
  IS NOT A SIZE SORT - BUT THE WORD "DIED" IS NOT EARNED (2026-08-13, `V6-B`).**
  `PREREG_v6b_dip_survival.md` committed **ALONE at `dc5ae98`**, a strict ancestor of every
  measurement commit. **ADOPTS NOTHING; no file under `valuation/` changed.** The register's own
  kill condition would have closed the branch at two sessions if the primary arm had failed. **It
  did not fail.**
  * **ARM 1 M1 IS REAL AND IS THE LARGEST REPLICATED EFFECT THIS PROGRAMME HAS PRODUCED IN A LONG
    TIME.** On **37,014 dipped rows** over 68 dates, `P(a further -20% within 126 trading days)` is
    **32.51% for the HEALTHY set against 43.35% for the unhealthy** - a **10.8pp absolute, 25.0%
    relative** reduction. The registered per-date statistic is **-10.228pp at HAC *t* -10.5847**
    against its own permutation p5 of -1.7072, **replicated in BOTH halves** (-9.064pp early,
    -11.515pp late), sign-stable, and clearing the **pre-committed 3.0pp economic floor** more than
    threefold. **The effect runs FOUR TO FIVE TIMES its own minimum detectable effect in every
    window** - the exact opposite of V6 and S19, where no cell reached detection at all.
  * **M3 CORROBORATES ON A DIFFERENT STATISTIC AND THE TAIL IS WHERE IT SHOWS** (+5.853pp, *t*
    +10.9212, clearing its bar in all three windows): forward 126d drawdown **p05 -0.4635 healthy
    against -0.6472 unhealthy - an 18.4-point shallower left tail** - and worst observed -0.8907
    against -0.9954.
  * **IT IS NOT A SIZE SORT, AND THAT IS THE CAVEAT THAT DECIDED THE RESULT.** C8 measured the
    healthy dipped set at **2.06x** the median market cap of the unhealthy one - U7's and S10's
    failure mode - so C8 was deepened into a within-size stratification, **labelled POST-HOC and
    carrying NO verdict**: **five of five market-cap quintiles negative, five of five clearing their
    own p5 full-sample, FOUR of five clearing both halves, smallest effect anywhere 3.787pp - still
    above the economic floor.**
  * **BUT THE GRADIENT CUTS AGAINST THE SHIPPED BOOK, AND THIS MUST TRAVEL WITH THE HEADLINE:
    -14.287pp in the SMALLEST quintile against -3.787pp in MEGACAPS**, which is also the one
    quintile that **fails** the both-halves leg. **The live hot list is megacap-tilted, so the claim
    is strongest exactly where the product is not.**
  * **THE WORD "DIED" IS NOT EARNED, AND THIS IS THE SENTENCE THAT MATTERS MOST.** The metric that
    separated is a further **-20%** - **DEEPENING, not DYING**. **M2, the actual bankruptcy /
    regulatory-delisting metric, is VOID - UNDERPOWERED BY CONSTRUCTION** at **42 distress events
    against a floor of 60 pre-committed before any count was read**, and **none of its numbers are
    quotable** (its early half fails its own bar at *t* -1.9683 against p5 -1.9683). **The earned
    sentence is about falling further, not about defaulting.**
  * **A PREMISE THAT REWROTE THE TASK'S OWN SECOND METRIC: 82.63% OF DELISTINGS ON THIS UNIVERSE
    ARE ACQUISITIONS** (585 of 708; bankruptcy 97, regulatory 13), every one also flagged
    `delisted`. So a naive `P(delisted)` principally measures **takeover probability**. Distress is
    `bankruptcyliquidation` + `regulatorydelisting` and nothing else. **AND MY REGISTERED MECHANISM
    WAS BACKWARDS:** I argued acquisitions would run AGAINST the healthy set; measured, the
    **UNHEALTHY** set is acquired **MORE** (0.292% vs 0.484%, ratio **0.604**), so a naive
    `P(delisted)` would have **EXAGGERATED** the healthy set's advantage rather than reversing it.
    **The rule was right and the reason I gave for it was wrong.**
  * **ARM 2 (the top-decile overlay) IS NULL ON BOTH HORIZONS**, and reported because a late-half
    figure this size invites quoting: 63d **flips sign between halves** (-0.095pp/yr early,
    **+10.919pp/yr** late, full +4.993pp at *t* +1.1188 vs p95 1.6421); 126d is sign-stable but
    clears neither half (+6.375pp full, *t* +1.3840). **C7 reads 11,426 top-decile rows over 69
    dates - the identical count S10 reported independently**, which is what makes this the same
    object the published `top_decile_alpha` describes. C8 shows the tilt runs the OTHER way here
    (dipped names inside the decile are **0.58x** the size of the rest), so Arm 1's size story and
    Arm 2's are not the same story.
  * **ARM 3 (dip x insider open-market buying) IS NULL - AND NOT ON COVERAGE**, which refutes half
    my own expectation: median **106** buy-flagged dipped names per date against a floor of 10.
    Full +1.147pp/yr at *t* +0.5904; the late half is **+0.011pp (*t* +0.0041)**, i.e. absent.
    **C6 confirms it is not the shipped theme renamed: Spearman against the `insider` theme is
    +0.2935.** Built from **`transactioncode` P only** - 124,181 open-market purchases with **zero**
    negative-share rows - because `transactionvalue` is **UNSIGNED** (0 negatives in 2.6M) and the
    shipped `_insider_score` silently **skips 2,182,601 rows (38.7%)** carrying neither price nor
    value.
  * **CONTROLS: C1 gated in its OWN pass** and reproduced the record to 16 digits; **C3 ZERO
    point-in-time violations** on all three routes, including that **no ACTIONS event dated on or
    before the rebalance date counts as a forward outcome**; **C4** 968 censored rows **DROPPED**
    rather than scored on a short window; **C6 FIDELITY - the healthy share of dipped rows is
    26.8%, reproducing V6's own 0.2683**, which is the proof the floors were not re-tuned (void
    condition 6.3).
  * **`V6-OPT` (cash-secured puts) IS UNLOCKED, inheriting three caveats**: the claim is about
    falling further and **not** defaulting; it is **weakest in megacaps**; and **V6 already showed
    this same population carries NO return edge** (four nulls), so a CSP case rests on the risk
    profile and the premium, never on expected appreciation.
  * **Equity `N` 206 -> 212.** Expectations **5 right, 2 wrong, 1 split** - and both misses are
    about MECHANISM rather than verdict. `data/free_analysis/V6B_DIP_SURVIVAL.json`;
    `HANDOFF_edge_audit.md` V6-B sections 0-11.
- **THE DIP DETECTOR'S CLAIM IS NOT SUPPORTED - FOUR ARMS, FOUR NULLS - AND THE USEFUL NUMBER
  IS THAT A DRAWDOWN IS SUBSTANTIALLY AN INVERSE-MOMENTUM SORT (2026-08-13, `V6`).**
  `PREREG_v6_dip_detector.md` committed **ALONE at `93e3e60`**, one `.md`, zero `.py`, a strict
  ancestor of every measurement commit - and **registered BEFORE the tab exists and before any of
  its copy was written**, which is the strongest ordering available. Measured, not assumed: no Dip
  Detector tab, no `V6` row anywhere, and the word "dip" appears nowhere in `valuation/`.
  **ADOPTS NOTHING; no file under `valuation/` changed.**
  * **ALL FOUR ARMS NULL** (20%/30% below a 252-day trailing high x 63d/126d). Full-sample
    vs-universe: **+0.585pp, +0.705pp, -0.480pp, +0.174pp**/yr; vs-unconditioned-dips **+2.108,
    +0.977, +2.081, +0.881**. Bars are **each leg's OWN within-date permutation p95** (500 draws,
    landing at *t* **1.44-1.86**). **X7's 2.2837 and 1.95pp were NOT quoted** - X7 calibrated a
    decile-book long-short *t* and a top-decile alpha margin, and this is neither object.
  * **THE FINDING THAT IS NOT THE VERDICT, AND IT IS THE ONE THE PRODUCT NEEDS: on this panel a
    drawdown is substantially an INVERSE-MOMENTUM SORT - Spearman(drawdown, `momentum` theme)
    = +0.6642** (`low_risk` +0.4196, `size` -0.2914, `value` -0.0834). **So a dip tab would
    systematically surface names the live composite is marking down** - two screens that disagree
    by construction. **I registered that correlation below 0.4 at 60/40 and was wrong**, and the
    register's "a drawdown is a different object" claim is half right: different from *short-term
    reversal* (which is not a panel column at all), **not** different from *momentum*.
  * **SEVEN OF EIGHT LEG-SERIES FLIP SIGN BETWEEN HALVES, ALL THE SAME WAY** - negative over
    2009-01-15 -> 2017-04-20, positive over 2017-10-18 -> 2026-01-28 (2017-07-20 embargoed).
    Session 7's LOO pattern again, but **systematic rather than scattered, which sharpens the
    warning: A DIP DETECTOR BUILT AND VALIDATED ON THE LAST EIGHT YEARS ALONE WOULD HAVE LOOKED
    LIKE IT WORKED.** The early half is the only thing that stops it. **Two half-cells clear their
    own p95 - both LATE, both on the dipped-vs-dipped leg** - A1 at *t* **1.6782 vs 1.6634, a
    margin of 0.0148**, and A4 at 1.6387 vs 1.4381. **1 arm of 4 clearing 1 half of 2**; the
    family-wise clause earns its keep for the fourth time.
  * **NULL MEANS "COULD NOT BE SEPARATED AT THIS RESOLUTION", NEVER "ABSENT" - QUOTE IT WITH THE
    MDE OR DO NOT QUOTE IT.** **No full-sample cell's observed effect reaches its own minimum
    detectable effect on either reference**: A1's dipped-vs-dipped **+2.108pp against an MDE of
    +3.371pp at the register's own bar** and +4.177pp at the conventional |*t*|=2. **Both
    references are reported deliberately** - a *t*=2 MDE against a p95 bar of 1.6 overstates how
    coarse the design is, and no MDE at all understates it. S19's lesson on a new instrument.
  * **THE CONDITIONING IS PARTLY A SIZE SCREEN, WHICH IS A CAVEAT ON THE DIPPED-VS-DIPPED LEG.**
    The floors keep only **26.8%** of dipped names at 20% (22.3% at 30%) and what they keep is
    **1.73x larger by median market cap** ($4.654B vs $2.690B; 1.82x at 30%). Since that leg
    compares conditioned names against ALL dipped names, part of it is large-dipped vs
    small-dipped - **U7's and S10's failure mode**. It does not threaten a NULL verdict.
  * **THE HEALTH FLOOR BINDS HARDER THAN QUALITY, REFUTING MY OWN REGISTERED PREDICTION.** Of
    37,982 dipped rows, quality alone keeps **41.15%** and health alone **35.88%** (both 26.83%).
    The 0-100 health scale's midpoint of 50 sits above the panel's own median health of **46.02**.
  * **THE PRIOR THE TASK CITED IS REAL BUT WEAKER THAN IT SOUNDS, AND WAS FIXED IN THE REGISTER
    BEFORE ANY RESULT.** `P4-3` rejected short-term reversal on **2026-07-29** - the 800-name era
    audit **B12** showed was an **ALPHABETICAL A-C slice**, which `CLAUDE.md` already lists as
    needing a full-universe re-run. **So this null is NOT a re-rejection of short-term reversal
    and may not be reported as one**; that item is still open.
  * **THE BINDING LIMIT, COMMITTED AS AN ASYMMETRY BEFORE THE RUN: the tab's own live sub-scores
    are NOT computable point-in-time** (quality needs a WACC, and **S23** measured that path
    fetching **LIVE Yahoo prices** to value 1999). The arm used the panel's `quality` theme plus a
    point-in-time health score that **CALLS the shipped `_health_score`** rather than retyping its
    breakpoints. **So a NULL here IS informative** - it used the panel's strongest theme, IC *t*
    **+3.10** - **but a POSITIVE would NOT have licensed the tab's copy** without a separate
    live-vs-panel fidelity check. *Coverage is not fidelity.*
  * **CONTROLS: C1 GATED AND RAN IN ITS OWN PASS** (`--controls-only` exits before any arm is
    scored - session 26's defect stays repaired), reproducing the record to **all 16 digits**;
    **C2** 69 dates / 2,531 names asserted not warned; **C3** zero point-in-time violations, pinned
    by a synthetic panel where a post-date crash must not move the flag; **C4** drawdown coverage
    **98.33%**, health **100.00%**, and **zero rows took the cash-burner branch** - reported, not
    silently routed; **C5 THE SPLIT TRAP PINNED FROM BOTH SIDES** - a 2-for-1 split reads as a
    **-50% drawdown on a RAW series and as no dip at all on the adjusted basis**, and since
    companies split **after they rise**, a raw basis would have flagged the strongest names in the
    universe; **C6** no per-ticker tail (B6).
  * **FOUR DEFECTS IN MY OWN INSTRUMENT, ALL CAUGHT BEFORE ANY VERDICT EXISTED.** A degenerate
    permutation draw crashed the run, and **treating it as 0.0 would have padded the null with
    fake draws and LOWERED the p95 - i.e. made the bar EASIER**; a test of mine could have passed
    vacuously and got a positive control; **two controls were pointed at column names the panel
    does not have** - C8 read `marketcap` where the panel's column is **`market_cap`**, so a
    `.get()` would have returned `None` and read as *"no size tilt"* rather than *"this control
    never ran"*, removing the only guard against reporting a size sort as a quality finding
    (U2's near-miss class); and a speedup **whose stated justification was false** - a 500-draw
    sweep costs ~2 seconds, not minutes, and on one leg the "optimization" is **slower** - kept
    only because it is **verified inert** (KS *p* 0.4599 / 0.5089).
  * **THE APP LANE SHIPPED THE TAB WHILE THIS WAS MEASURING IT, AND BUILT THE SAME MECHANISM
    INDEPENDENTLY - SO THE CLOSE-OUT WAS DONE ON THEIRS.** `6b7c358` landed **twelve minutes
    before this pushed**, carrying `valuation/web/dip_posture.py`: modelled on the same
    `score_confidence.py`, owning the copy, pinned by test, with a three-state `STATUS`
    (`OPEN`/`POSITIVE`/`NULL`) explicitly gated on **this register** and a designed close-out.
    **Creating a second module owning the same copy is the exact defect both lanes wrote their
    docstring to prevent**, so `STATUS = NULL` and the verdict fields were filled on theirs;
    **39/39 `test_dip.py` pass.** **Their design is better than mine in one respect and it should
    be carried forward: they enumerated what may never be said in ANY state** - a `BANNED` tuple
    (*"buy the dip"*, *"will recover"*, *"oversold"*, *"sentiment-driven"*) asserted **against the
    RENDERED payload, not the source**, because rendering is where copy leaks.
  * **TWO DEFECTS THE CLOSE-OUT EXPOSED, both invisible until a real verdict existed, and the
    second is the serious one.** **(a)** `REGISTER` cited **`PREREG_v6_healthy_drawdown.md`, a file
    that does not exist** - the register is `PREREG_v6_dip_detector.md` - against a docstring
    saying the citation is there so a reader *"can check that the file exists rather than taking
    the citation on trust"*. Two lanes named the same unbuilt thing differently, which is the
    ordinary cost of registering ahead of a product; the replacement test now asserts **the file is
    on disk** rather than that the string starts with `PREREG_`. **(b) A NULL VERDICT WOULD HAVE
    SILENTLY UNBLOCKED AN OUTBOUND PUSH.** `digest_eligible` was `STATUS != OPEN`, under the comment
    *"an outbound push of a dip list is a recommendation-shaped message, so it waits for the
    evidence"* - but **a NULL is evidence NOT arriving**, so its arrival would have flipped the
    digest ON. The rule it came from (*a NULL must be exactly as reachable as a POSITIVE*) is right
    and the **copy** still obeys it; it had been carried one step too far, because **the digest does
    not push the verdict, it pushes a LIST OF NAMES.** Now `STATUS == POSITIVE`, so the close-out
    leaves the push where it was rather than opening it. **ROUTED, NOT DECIDED - whether a dip list
    should ever go out is Don's and the app lane's call.** `PT-OUTBOUND`'s family, caught before it
    could fire.
  * **THIS IS THE ONE PLACE V6 TOUCHES `valuation/web/`, AND IT IS A SCOPE CHANGE AGAINST THE
    REGISTER'S OWN SECTION 8, MADE AFTER THE RESULT EXISTED - DECLARED, NOT ABSORBED.** The
    alternative was leaving a **live** surface telling users *"we are testing it, and this page will
    say the answer when the register closes"* after it had closed - the module's own stated failure
    mode (*"Prose in a template does not stop; someone has to remember"*). Both changes move the
    product **more** conservative, and neither touches an arm.
  * **THE EXPLAINER CONSTANT IS NAMED AND IS THE APP LANE's TO BUILD:
    `valuation/web/dip_confidence.py`**, modelled on the shipped `valuation/web/score_confidence.py`
    (V3's precedent - one module owns the calibrated wording, pinned **verbatim** by a test).
    **`VERDICT = "NULL"`**, and the tab may call the screen **a filter, not a forecast**: it finds
    names well below their recent high, and the project has **not** shown they beat the market.
    **AMENDED BY THE CLOSE-OUT ABOVE: V6 touches `valuation/web/` in exactly ONE file,
    `dip_posture.py`, and nowhere else** - the boundary the register set
    before the result existed.
  * **Equity `N` 202 -> 206**, re-measured from `research_log.detail()` after this session's merge
    rather than quoted from this file - the S17/S19 defect, not repeated. Expectations **3 right,
    4 wrong, 1 split**. `data/free_analysis/V6_DIP_DETECTOR.json`; `HANDOFF_edge_audit.md` V6
    sections 0-11.
- **THE "CONVEX OVERLAY AS INSURANCE" IS NOT INSURANCE — IT IS LEVERAGE, AND IT LOSES THREE TIMES
  WHAT IT WAS SUPPOSED TO BE DIVERSIFYING; THE U-SERIES IS NOW CLOSED, THREE OF ITS ROWS BY DESIGN
  MEMO RATHER THAN BY MEASUREMENT (2026-08-13, session 37, `U3`+`U4`+`U6`+`U8`).**
  `PREREG_u3_convex_overlay.md` committed **ALONE at `9603e64`** — one `.md`, zero `.py`, a strict
  ancestor of the measurement commit. Frozen books on both sides, no panel rebuild. **ADOPTS
  NOTHING.** `U4`/`U6`/`U8` are `DESIGN-RECORDED` in `DESIGN_u4_u6_u8.md` at **zero trials** —
  the task asked for memos where a memo is the honest deliverable, and no backtest was
  manufactured for them.
  * **THE AUDIT'S PREMISE IS REFUTED BY MEASURING WHAT THE SLEEVE IS MADE OF.** It calls the
    options book a long-volatility sleeve *"built by accident"* whose conditional correlation to
    the equity book *"is the whole question"*. Measured: `opt_right` is **`call` on 3,870 of
    3,870 rows** at mean delta **+0.3725** — long vega **AND** long delta. Correlation with the
    equity top decile **+0.4371**; in the equity book's worst four covered quarters the sleeve
    returns **−84.39%** against its own **+27.52%** average quarter; in **COVID 2020Q1 the equity
    top decile fell −28.09% and the sleeve fell −76.14%**. **No capital weight can make this
    insurance.**
  * **`A1` REJECTED AT BOTH O11 CONCURRENCY CAPS, AND NOT MARGINALLY: MAXIMUM DRAWDOWN IS WORSE
    THAN THE EQUITY BOOK ALONE IN ALL TWENTY CELLS** (cap 10 ΔmaxDD −0.0002 to −0.0021; cap 50
    −0.0048 to −0.0480), improving **monotonically toward X = 100** — so a drawdown-minimising
    optimiser puts **ZERO** in the sleeve, which is `U8`'s answer for free.
  * **THE AUDIT'S OWN TWO-LEG BAR IS WHAT CATCHES IT, AND IT EARNED ITS KEEP.** Sharpe **does**
    improve at cap 10 (1.1296 → **1.2041** at X=96) — purely by **raising return** (+27.01%/yr →
    +34.19%/yr). That is exactly the case `:1284` disqualified in advance: *"a long-vol sleeve
    that improves Sharpe by raising return is not doing the job it is being hired for."* **A
    one-leg Sharpe bar would have adopted this.**
  * **THE AUDIT CONTRADICTS ITSELF AND MEASUREMENT SETTLES IT.** Its step 2 (`:1279`) conditions
    on the equity book's worst decile — **precisely the return-based conditioning its own
    `:1282` warns is an artefact** — and the two give **OPPOSITE SIGNS**: **−0.6504**
    return-conditioned on n=4, against **+0.5478** and **+0.5819** on the high- and low-IV halves.
    **The conditional MEAN is the informative statistic; the conditional CORRELATION is the trap.**
  * **THE ASYMMETRY WAS FIXED BEFORE THE RUN, from the audit's own `:1549`**: a crash-insurance
    rule cannot clear a both-halves gate unless the sample holds two comparable crashes and this
    one holds **one** (S10's trough index 44 of 69). So the register committed that **a decisive
    REJECT was available and a decisive ADOPT was not** — a clearing arm would have been recorded
    `ELIGIBLE-BUT-UNRESOLVED`, never adopted. **Nobody may read this rejection as evidence that
    portfolio insurance does not work.**
  * **NON-BLINDNESS DISCLOSED IN THE REGISTER (§0.5), not after.** A crude probe of A2's **sign**
    was run before the register existed, to decide whether U3 was measurable at all. The register
    says so, excludes that expectation from scoring, and leans on the audit's **verbatim** bar
    rather than one chosen afterwards.
  * **COVERAGE: 40 of 69 quarters, 28 uncovered EARLY and 1 late**, halves **20 and 19** after
    embargoing 2021-01-21 — **S18's and U2's situation for the third time**, so a full-panel gate
    is impossible rather than weak.
  * **`U6` IS NOT BUILDABLE AND THE REASON IS A NUMBER: 1.81% CHAIN COVERAGE.** Of **7,132**
    names entering the top decile over 68 transitions only **129** have mined chains; **median 2
    per rebalance** against a mean top-decile size of **165.6**, and **ZERO on 18 of 68 dates**.
    ~~Second, independent blocker: the entry leg is a cash-secured **put** and the cache is
    **100% calls**, so no put-chain history exists to replay against.~~ **RETRACTED 2026-08-13
    (`V6-OPT`), against my own prior session: THE CACHE IS NOT 100% CALLS.** That measurement —
    `opt_right == "call"` on 3,870 of 3,870 rows — is of the **TRADED BOOK**, and the **CACHE**
    was never checked. Measured: `data/options` holds **1,288,750 puts against 1,288,751 calls**
    across 40 sampled tickers, **exactly 0.5000 put share, ZERO tickers with no puts**, with bid,
    ask, volume and open interest; `data/options_derived` carries the same contracts with `iv`,
    `delta`, `mid` and `spread_frac`. **`V6-OPT` then priced 2,038 real 25-delta puts from that
    cache and settled them to expiry.** The **coverage** blocker is untouched and still carries
    U6's verdict on its own, so the row's status does not change — but it rests on **one**
    measured reason, not two. **A composition fact about a BOOK is not a coverage fact about a
    CACHE.** Same class as `S25` and `B13` — **unobtainable without new data**, and it stays the
    most tradeable idea in the catalogue if the data is ever bought.
  * **`U4`'s GATE HAS RESOLVED, NEGATIVE.** It was gated on `U1`/`U2`; both rejected, as did
    `U7`. So one object may carry **two independently-sourced expressions with an explicit
    statement that they are independent** — no combined score, no combined confidence, no arrow
    from view to trade. And **O11 forces an addition to the copy rule**: expectancy framing is
    necessary but **not sufficient**, so any surface quoting per-trade expectancy must quote the
    survivability result beside it.
  * **A DEFECT IN MY OWN INSTRUMENT, PRESENTATIONAL AND PROVEN SO RATHER THAN ASSERTED.** A3's
    column was named `drag_vs_equity_pp` while computing `combined − equity`, which is **positive
    when the sleeve adds return** — a gain printed under a loss's name. Renamed; the pre-fix and
    post-fix artifacts diff at **344 shared leaves, ZERO moved, 6 added, 0 removed.** Also
    disclosed: the combined book is **rebalanced to weight X every quarter** per the register, so
    the sleeve's geometric **−33.35%/yr** coexists with a **+27.52%/quarter arithmetic** mean and
    the construction **tops the sleeve back up after a crash quarter**, which flatters it.
  * **CONTROLS: C1 reproduces the record at alpha 0.07174142332098163; C3 ZERO look-ahead over
    161,610 marks; C4 `top == alpha + equal_weight` at max abs deviation 0.000e+00; C5 at ρ = 1.0
    the largest improvement is +0.000e+00; C8 X=100 reproduces the equity book at 0.000e+00.
    C7 is the one that cuts: the sleeve is closer to the equal-weighted universe (+0.4837) than
    to the top decile (+0.4371), so it is BETA, not book-specific.**
  * **THE ONLY PRODUCTION CHANGE IS ONE ADDITIVE KEY**: `quantile_backtest`'s opt-in `series`
    dict now carries `equal_weight`, because `top = alpha + equal_weight` is an identity and **you
    cannot compound an alpha**. Inside the existing `return_series` gate, so every current
    caller's payload is bit-identical; pinned by test. **Options `N` 285 → 287** (A1 and A2; A3
    charges nothing); **equity untouched at 190**. Expectations **4 right, 2 wrong, 1 excluded**.
    `data/free_analysis/U3_CONVEX_OVERLAY.json`; `HANDOFF_optionsbot.md` §56.
- **THE OPTIONS SURFACE IS GENUINELY ORTHOGONAL TO THE EQUITY PANEL AND PREDICTS NOTHING WITH
  THAT ORTHOGONALITY — THE AUDIT'S CENTRAL PREMISE IS CONFIRMED AND ITS CONCLUSION REFUTED, AND
  THE LAST LIVE DIRECTION OF THE UNIFICATION IS NOW SHUT (2026-08-13, session 36, `U2`).**
  `PREREG_u2_surface_stock_signals.md` committed **ALONE at `e8e222b`** — one `.md`, zero `.py`,
  a strict ancestor of the measurement commit. No panel rebuild. **ADOPTS NOTHING.**
  * **THE ROW CLOSES `PARTIAL`, NOT `DONE`, AND THE REGISTER FIXED THAT BEFORE ANY RESULT.** The
    audit's U2 names four features; this tested the **levels** and declined two. **The put–call
    parity deviation on matched strikes — Cremers–Weinbaum's ACTUAL measure and the largest
    effect the section cites (51 bps/week) — needs matched call/put pairs from the raw chains and
    is a NEW feature**, which the task forbade; the 21-day changes are a different hypothesis
    (surface *momentum*, not surface *level*). **Neither is a null.** Marking the row `DONE`
    would tell the next session they had been tested. S10's precedent.
  * **A DUPLICATE ARM KILLED BEFORE THE REGISTER: `skew_25d` IS EXACTLY `iv_put_25d −
    iv_call_25d`**, max |Δ| **0.000e+00** over 217,706 rows. So the audit's separately-named
    *"ATM call-minus-put implied-vol spread"* is, at 25 delta, **exactly `−skew_25d`** — one
    column and its negation, whose rank ICs are exact negatives. **ONE arm, not two.** This is
    the `illiq`/`spread_pct` defect class the O3/O4/O5 lane found in a prior lane's panel,
    **caught before the register rather than after the verdict**, and pinned by C5.
  * **THE NEAR-MISS THAT WOULD HAVE ANSWERED A DIFFERENT QUESTION ENTIRELY: the shipped
    `term_slope_60_30` is NOT the O16-validated construction.** It is exactly `atm_iv_60 −
    atm_iv_30`; O16 validated `atm_mid − atm_front`. **Spearman between them is only 0.5281** on
    the covered names. A lookup by column name computes cleanly, raises nothing, and **reports a
    U2 verdict on a construction O16 never validated** — while O16's whole finding was about
    separating `term_slope` from a front-end IV level. The arm uses **`atm_iv_60 −
    atm_iv_front`** and a **source-level test pins that the shipped column never enters the arm
    path**.
  * **COVERAGE FORBIDS A FULL-PANEL GATE — AN IMPOSSIBILITY, NOT A POWER CAVEAT.** The derived
    layer spans **2016-01-04 → 2025-12-31** against a panel starting **2009-01-15**, so **29 of
    69 rebalance dates carry ZERO coverage and ALL of them are early**; the final date
    (2026-01-28) is uncovered too. **Every split is of the COVERED SUBSAMPLE — 40 dates, 20 and
    19 after embargoing 2021-01-21**, both above the shipped `min_dates=16`. **S18's situation
    exactly, and the same replacement.** A pass on 20-date halves is not the same object as a
    pass on 34-date halves. Coverage is **~25%** of the panel cross-section (mean **436.9** names
    per covered date), better than the audit's predicted 4–14%.
  * **ALL FOUR ARMS REJECTED** against X7's calibrated **2.71** theme-IC bar in both halves.
    Incremental IC *t*, full sample: `term_slope` **+0.9862**, `iv_rank` **+0.1931**, `skew_25d`
    **+0.3471**; the composite **+0.7797 / +0.1508** across its two decide-then-measure
    directions. Raw IC *t*: **+0.6729**, **+0.0377**, **+1.4870**.
  * **THE HEADLINE IS THE DISSOCIATION, AND IT SETTLES THE AUDIT'S ARGUMENT IN BOTH DIRECTIONS.**
    The audit's case was that an options-derived signal is *"structurally orthogonal to
    everything already in the panel"* — and **it is: the seven incumbents explain only 5.5% to
    8.8% of these features' variance**, against **41.3% of `gp_on_capital`** and **78.4% of
    `ret_6_1`**. **The features really are new information. The new information does not
    predict.** Orthogonality was the audit's reason for expecting value and it is confirmed;
    what fails is the prediction, not the premise.
  * **THE POWER CONTROL THE AUDIT ITSELF DEMANDED CLEARS, SO THESE NULLS ARE INTERPRETABLE —
    AND THE SAME NUMBER CUTS AGAINST THE VERDICT.** `gp_on_capital` **2.4776** and `ret_6_1`
    **2.4762** on the identical covered rows, against the audit's 2.0 bar. **But both land BELOW
    2.71**, so the panel's own best-known signals would *not* clear the bar the arms were judged
    against on this subsample. **And there is NO valid power control for the INCREMENTAL
    statistic at all**, because every known-real signal here is already an *input* to an
    incumbent theme (which is exactly why their R² is 41% and 78%). Reported, not glossed.
  * **THE SMIRK'S PUBLISHED SIGN DOES NOT REPRODUCE.** Xing–Zhang–Zhao's negative direction was
    **declared before the run**; measured, `skew_25d`'s raw IC is **POSITIVE** (median +0.02056,
    *t* +1.4870). Far too weak to refute a published result — but on this megacap universe the
    declared direction is **not reproduced**, and a positive result on it could never have been
    a pass. Same shape as O3/O4/O5's sign reversal.
  * **C6 REFUTES THE OBVIOUS ALTERNATIVE OUTRIGHT.** A volatility-surface feature is a prime
    candidate to be a volatility theme in a new costume (U7's failure mode). The largest |mean
    per-date correlation| against ANY incumbent is **0.0844** (`skew_25d` vs `momentum`), and all
    three sit under **0.05** against `low_risk`. **These are not repackaged incumbents.**
  * **CONTROLS: C1 reproduces the record to 1e-9; C3 ZERO point-in-time violations over 17,411
    joined cells** — the join is **STRICTLY BEFORE** the rebalance date, stricter than `fwd_ret`
    requires, to remove the argument rather than win it; C5 no arm is another arm's negation.
    **The book gate and the 2.2837 long-short floor were NOT run and are NOT quoted**: the
    register runs them only on an eligible composite. **Both calibrated bars would be
    EXTRAPOLATIONS here in any case** — they were measured on the full 69-date 2,531-name panel.
  * **A DEFECT IN THE SHIPPED IC ARITHMETIC, REPORTED NOT REPAIRED, AND IT IS THE
    `SECTOR-NEUTRAL-B6` ZERO-VARIANCE GUARD IN A NEW PLACE.** `theme_ic`'s guard is `if sd > 0`,
    and whether a constant series has an exactly-zero floating-point sd is **value-dependent**:
    `[0.1, 0.1, 0.1]` has sd ≈ 5.8e-17, so the guard passes and the *t* comes back **~1.0e16**.
    Not repaired here, because repairing it would make this lane's copy stop being the shipped
    arithmetic and X7's 2.71 would then apply to a statistic it was not calibrated on. A
    degeneracy check gates the verdict instead, so an absurd *t* can never be READ as a pass.
    **Edge lane's to fix.**
  * **THE SIGNAL-TRANSFER DIRECTIONS OF THE UNIFICATION ARE NOW ALL CLOSED, AND THAT IS NOT
    THE SAME AS CLOSING THE U-SERIES**: `U1` REJECTED (composite → options entry), `U7` REJECTED
    (composite as an options veto), `U2` REJECTED on its level half and `PARTIAL` on the row.
    **FOUR U-ROWS REMAIN OPEN** — `U3` convex overlay, `U4` one decision object, `U6` CSPs in,
    `U8` one risk budget. None is a signal-transfer question, but the O-series discipline
    applies: do not report a series closed while its rows are open. **CLOSED 2026-08-13 (session
    37), and the distinction survives the closure: `U3` closed by MEASUREMENT (rejected), while
    `U4`/`U6`/`U8` closed `DESIGN-RECORDED` — a design record is NOT a measurement, and anyone
    re-opening one of those three re-opens a live question rather than a settled one.** **Equity `N` 185 → 189 for this item's four arms — though it reads
    190 after the concurrent `S14-WIDTH` landing the same day, which is why an equity figure
    must be RE-READ from `by_domain` after every merge and never quoted from a session's own
    mid-run measurement.** Expectations **5 right, 3 wrong, 1 split** — and the streak breaks: this is the first
    session in five in which **no** arm cleared **either** half.
    `data/free_analysis/U2_SURFACE_STOCK.json`; `HANDOFF_optionsbot.md` §55.
- **THE S-SERIES RESEARCH ROWS ARE CLOSED: TWELVE ARMS, TWELVE NULLS — AND BOTH NULLS ARE THE
  INFORMATIVE KIND, ONE BECAUSE IT IS NOT INERT AND THE OTHER BECAUSE IT COULD NOT HAVE DETECTED
  WHAT IT WAS HUNTING (2026-08-13, `S17`+`S19`).** One register for both,
  `PREREG_s17_s19_events_mdna.md`, committed **alone at `a92996d`**. **ADOPTS NOTHING.**
  * **`S17`'S METHOD STEP 1 CANNOT BE EXECUTED, AND THAT IS PERMANENT UNTIL `D10` RUNS.** The
    audit says *"obtain the code legend from Sharadar's documentation"*. **Sharadar ships no
    legend with the EVENTS download** (`bulk.py:20`, `:235`) and `D10` records the docs were
    never extracted. So the codes were tested **BY NUMBER, UNLABELLED** — and the register said
    in advance what that costs: **a signal on an unlabelled code is uninterpretable even if it
    works.** A positive would have been a lead requiring the legend, never an adoption. **Do not
    re-run `S17` without the legend** — it would buy the same uninterpretable numbers for another
    10 trials.
    * **CORRECTED 2026-08-20 (`SC-2`, zero trials): THE LEGEND EXISTED, IN THIS REPO, TEN DAYS
      BEFORE `S17` CLOSED.** `SHARADAR_REFERENCE.md` landed at **`47cb189` on 2026-08-03** with
      the full **37-code `EVENTCODES` legend** transcribed from the live API; `S17` closed
      2026-08-13. **The premise above holds and the inference does not:** Sharadar genuinely
      ships no legend *with the bulk download* — the reference says so of itself — but it had
      already been pulled and committed, so "tested BY NUMBER, UNLABELLED" and "PERMANENT UNTIL
      `D10` RUNS" are both wrong. **`S17`'s five arms are 91 Financial Statements and Exhibits,
      71 Regulation FD Disclosure, 81 Other Events, 52 Departure of Directors or Certain
      Officers, and 34 Schedule 13G Filing.** **NO VERDICT MOVES** — all ten arms are still NULL
      and nothing re-opens them. **AND A CANDIDATE MECHANISM FOR THE ERA-CONCENTRATION, A LEAD
      AND NOT A FINDING: codes 34 and 35 STOP — 13G on 2024-12-17, 13D on 2025-05-16 — while
      91, 71, 81 and 52 all run to 2026-07-31.** A code that stops being emitted 13 months
      before the panel ends is era-concentrated *by construction*. **Its limits are the point:
      it can touch at most ONE of the five arms, so it cannot explain 91's or 71's
      era-concentration — the two `S17` reports in detail — and `S17`'s halves split around
      2017, so a 2024 sunset sits deep inside the late half rather than at the boundary.
      Whether it drives anything is UNMEASURED.** **The gated `S17` successor is NOT licensed
      by this correction**; it charges trials and needs its own blind register.
  * **THE MECHANISM QUESTION IS ANSWERED *NO*, AND THE PROJECT HAD ALREADY MEASURED IT.** The
    empirical decode that identified code 22 scored every registered arm on the way past
    (`bulk.py:243-247`): day-of median absolute return against a 1.292% baseline — **code 22 at
    1.64×**, and **91 1.15×, 71 1.13×, 81 0.98×, 52 0.96×, 34 0.94×**. Code 22's mechanism is an
    *information shock* and PEAD is drift **following** it; **the other codes have no shock for
    drift to follow.**
  * **BUT THE ARMS ARE NOT INERT, WHICH REFUTES MY OWN PRIOR WHILE THE VERDICT MATCHED IT.** All
    10 are **NULL** — **not one clears the both-halves leg** — yet **8 of 10 clear their own
    permutation p95 full-sample, 8 of 10 survive Benjamini–Hochberg at q 0.05, and ALL TEN are
    sign-stable across halves.** Annualised: code 91 **−2.2%**, code 71 **−2.0%**, code 34
    **+3.2% to +4.9%**. **They fail by being ERA-CONCENTRATED** (code 91 early *t* −3.476 / late
    −1.862; code 71 early −1.342 / late **−3.098**). **The register's hedge — day-of VOLATILITY
    is not directional DRIFT, and the two come apart for scheduled or slow-diffusing events — is
    the load-bearing part, not the prior it hedged.**
  * **"8 OF 10 CLEAR" IS NOT EIGHT FINDINGS, AND THIS CAVEAT MUST TRAVEL WITH THE NUMBER.** Two
    dependencies stack. **By construction the ten arms are FIVE signals at TWO horizons, and a
    code's 21d and 63d arms share a BIT-IDENTICAL event indicator.** **Measured**, the codes
    correlate up to **0.4227 (91~71)** at name-date level (mean |ρ| 0.1330 over 93,997
    name-dates) and the four negative codes all point the same way. **Effective independent tests
    are nearer three or four** — the SELRULE lesson, where 16 co-moving countries were worth 2–4
    draws — so **BH was fed correlated tests.**
  * **TWO EXPLANATIONS REFUTED BY MEASUREMENT, WHICH IS WHY THE ARMS ARE INTERESTING RATHER THAN
    DISMISSABLE.** They are **NOT market-cap sorts**: median cap of event vs non-event names is
    **0.93×** for code 91 and **1.07×** for code 71 (only code 81, the weakest arm, tilts at
    1.86×), so **U7's and S10's failure mode does not apply.** And **differential survival is not
    the driver** — drop rates 2.4–3.2% with gaps **under 1pp on every negative arm**.
  * **CONTROLS. C1 GATES AND RAN IN ITS OWN PASS**, aborting before any arm on failure — session
    26's defect repaired. Code 22 reproduces at **1.7423×** against 1.64×. **The ordering of the
    other codes reproduces only BROADLY, stated rather than rounded into a clean pass:** 91 and
    71 swap (within 0.007, effectively tied) and code 11 moves up two places. **C3 refutes the B6
    signature directly: 89.1% of names in the earliest cross-sections were still trading ten
    years later**, where a per-ticker tail drives that toward zero. 328 month-ends, cross-section
    median **1,649**.
  * **`S19`: BOTH ARMS NULL — AND THE NULL DOES NOT MEAN THE EFFECT IS ABSENT.** On **418
    held-out names with ZERO overlap** with the original 195 (15,893 filing pairs newly collected,
    **2.2×** the original study): **A1 `mdna_cosine_tf`@21d residual IC +0.012202 at NW *t*
    +1.1876**, **A2 `mdna_jaccard`@63d +0.021737 at +1.4012**. Neither reaches the audit's 2.0.
  * **THE SIGN DID NOT REVERSE AND THE MAGNITUDES GREW.** The register fixed the direction in
    writing first — *more MD&A change → outperform* — and **all four half-cells are POSITIVE**,
    against the original's own **+0.009607 at *t* 0.6463**. A sign flip between halves is this
    project's most repeated failure pattern and **it did not happen here.**
  * **THE DESIGN COULD NOT HAVE RETURNED A POSITIVE VERDICT EVEN IF THE EFFECT WERE EXACTLY TRUE
    — QUOTE THIS WITH THE NULL OR DO NOT QUOTE IT.** A1's **minimum detectable incremental IC at
    |*t*| = 2 is +0.020549** (A2's +0.031026) against an original effect of **+0.0096**. Its
    observed +0.0122 sits **below its own detection threshold**. **NULL means "could not be
    separated from zero at this resolution", NEVER "absent"** — V2G's lesson on a new instrument.
  * **THE BINDING CONSTRAINT IS THE PANEL'S FREQUENCY, NOT THE NAME COUNT, so collecting more
    names cannot re-open it.** MD&A scores start 2016-08 against a panel starting 2009-01-15, so
    **41 of 69 dates are covered and all sit late** — a full-panel both-halves gate is
    **impossible, not merely weak** (`S18`'s class) — and the original tested **111 MONTHLY**
    dates while the theme panel is **QUARTERLY**. Re-opening needs a **monthly theme panel**, a
    rebuild with its own register.
  * **C6 REPRODUCES ONLY LOOSELY AND THE EVIDENCE IS CONTRADICTORY, reported rather than rounded.**
    It passes on the **corrected** panel (+0.011227 vs the published +0.009607) while the **VOID
    pre-B6 panel matches the original's date count exactly (37 vs 37)** and its IC not at all.
    **Most likely neither banked panel IS the original's** — `lazy_prices_ic` builds its own.
    **A finding in passing: the original study's orthogonality block was computed on a pre-B6
    panel the project has since declared VOID**, so its numbers may not be quoted as
    corrected-panel measurements.
  * **`S10`'s ACCOUNTING HALF WAS ASSESSED FOR THIS REGISTER AND EXCLUDED, ON MEASUREMENT.** Every
    SF1 input for Beneish, Altman and external financing **exists** in the export, but **eight
    columns are absent from `WRDSProvider._KEEP`** (`assetsc`, `ppnenet`, `depamor`,
    `workingcapital`, `retearn`, `liabilities`, `ncfcommon`, `ncfdebt`), so it forces a **panel
    rebuild** where `S17`/`S19` needed none; **NT filings are not buildable from anything we own**,
    so the audit's *"flagged by two or more"* of **four** would silently become **two of three** —
    a different rule chosen after seeing what exists. **Still OPEN, scoped, charged nothing.**
  * **A DEFECT IN MY OWN REGISTER, CORRECTED HERE AND NOT EDITED AWAY.** §7 says *"equity `N` 186
    → 198"*; **186 was quoted from this file instead of re-measured after the session's own
    merge**, which brought in `U2`'s four equity trials. **The honest figure is `N` 190 → 202**
    and the charge of 12 is unchanged. **This is the exact error the record already warns about**
    — *re-read `by_domain` after merging* — committed with the warning in view.
    **`BACKTEST_RESULTS.json` was ALREADY stale at 186 against a live 190 before this session
    touched it**, so the refresh corrects `U2`'s drift too.
  * **Equity `N` 190 → 202.** Expectations **8 right, 0 wrong — and the sweep should be
    discounted, not celebrated:** three of the eight predicted NULL in a project where
    essentially everything is null, and **the reasoning behind the `S17` call was wrong even
    though its verdict was right.** Both ledger rows were `src=auto` and wrong — the **eleventh
    and twelfth** *"no section"* note to be false. `data/free_analysis/S17_EVENT_CODES.json`,
    `S19_MDNA.json`; `HANDOFF_edge_audit.md` S17+S19 §0-11.
- **THE NO-TRADE BAND'S KNEE IS IDENTIFIED AND IT IS EXACTLY WHERE THE BOUNDARY WAS — GIVEN THREE
  WIDER WIDTHS, BOTH HALVES STILL PICKED 0.30, SO `S14` IS NOW AN ADOPTION DECISION FOR DON
  (2026-08-13, `S14-WIDTH`).** `PREREG_s14_width_extension.md` committed **alone at `e63295e`**.
  **ADOPTS NOTHING — it routes a decision.** The grid gained 0.40, 0.50 and 0.75 (round
  extensions, nothing finer, `enter_frac` untouched) and the identical decide/held-out procedure
  re-ran in both directions.
  * **OUTCOME (a) OF THREE COMMITTED IN ADVANCE: THE OPTIMUM IS INTERIOR.** 0.30 is the argmax on
    **both** halves against three wider candidates, so session 35's grid-boundary caveat is
    **DISCHARGED, not repeated.** Net alpha by width, early / late: none +1.11/+10.94, 0.12
    +0.87/+11.88, 0.15 +2.02/+12.17, 0.20 +2.08/+11.91, 0.25 +2.17/+12.39, **0.30
    +2.88/+12.72**, 0.40 +2.32/+12.44, 0.50 +2.56/+11.84, 0.75 +2.74/+9.14.
  * **THE PORTABLE LESSON IS A CORRECTION TO MY OWN REASONING, NOT TO SESSION 35's: A BOUNDARY
    ARGMAX IS EVIDENCE THAT A GRID IS UNINFORMATIVE ABOUT WHAT LIES BEYOND IT — IT IS NOT EVIDENCE
    THAT THE OPTIMUM LIES BEYOND IT.** I registered the opposite lean at 60/40 and the extension
    moved the answer not at all. 0.30 happened to be both the boundary and the maximum.
  * **THE MECHANISM IS MEASURED, AND IT BOUNDS THE AXIS. Gross alpha PEAKS at exactly 0.30 on BOTH
    halves and falls away** (late +12.77 → **+13.79** → +13.33 → +12.56 → **+9.65**), because the
    cost saving is **capped** and staleness is not — at 0.30 the drag is already down to
    0.0127/0.0106, so at most ~1.1–1.3pp more exists even at zero turnover. **And the freezing
    argument, derived from the CODE before running, is now measured: the book's incumbent share
    climbs 0.359 → 0.701 at 0.30 → 0.943 at 0.75**, i.e. at 0.75 the book replaces one name in
    sixteen per rebalance and has largely stopped selecting. `_band_select` holds book SIZE fixed,
    so at an exit rank equal to the universe the book **FREEZES** — pinned by test.
  * **WHAT IT DOES NOT ADD, STATED PLAINLY: NO NEW HELD-OUT EVIDENCE ABOUT THE SIZE OF THE
    EFFECT.** The pick did not move, so the held-out measurement is **numerically identical** to
    session 35's (+1.780125pp / +1.768484pp, agreeing to **ten decimals**). The trial buys the
    **LOCATION** finding only.
  * **THE KNEE REPLICATES IN LOCATION BUT NOT IN SHARPNESS.** Decisive on the late half (0.30 →
    0.75 costs **3.59pp**); nearly **FLAT** on the early, where 0.75 is second best at **+2.74pp**,
    only **0.14pp** below the peak. **An adopt at 0.30 is well supported by the late half and
    weakly by the early one.**
  * **A DEFECT IN MY OWN CONTROL, AND IT MOVED NOTHING.** C3's first cut asserted **LIST** equality
    of the no-band book against plain top-N and failed **176 of 200** — `_band_select` returns
    survivors **first**, so the ORDER differs while the **SET is identical (200/200)**. Proved
    harmless rather than argued: a strict-rank selector swapped into the real panel moves every
    reported field by at most **2.13e-14** (the book is equal-weighted, so only the set can reach
    a number). **ZERO verdict cells moved.** **Session 35's C6 is also corrected: the EARLY-half
    surface is non-monotone too**, its monotonicity having been an artefact of the grid stopping
    at its own argmax.
  * **CONTROLS: C4 book size IDENTICAL at every width** (154.1 names early, 175.6 late), so no
    comparison is confounded by book size — S23's dilution mechanism cannot be operating here;
    **C2 turnover strictly decreasing across all nine settings on both halves** (0.75 runs about a
    fifth of the no-band book **and still loses**); **C1b all 48 shipped-width cells reproduce
    session 35's raw artifact at max |Δ| 1.33e-15.**
  * **FOR DON, AND THIS IS THE DECISION.** Width **0.30**, +1.78pp/+1.77pp net alpha held out,
    turnover roughly halved. It is **already live in the `taxable` configuration**, so an adopt
    changes the **DEFAULT**, not whether the band exists. It is a **VINTAGE EVENT**: the vintage
    was **DERIVED, not assumed** — **vintage 3, run 2, opened 2026-08-11, OPEN, i.e. TWO DAYS
    OLD** — so adopting resets the five-year clock a second time inside three days. And **roughly
    half the gain is a SIGNAL effect**, not the deterministic cost saving the original framing
    claimed. **B13 is only PARTIAL.**
  * **A THIRD EXTENSION IS FORBIDDEN by the register**, and the surface is documented end to end.
    **Equity `N` 185 → 186.** Expectations **2 right, 4 wrong, 1 split** — four of the five misses
    are the same invalid inference above. `data/free_analysis/S14_WIDTH.json`;
    `HANDOFF_edge_audit.md` S14-WIDTH.
- **THE NO-TRADE BAND CLEARS — THE FIRST ARM TO DO SO IN EIGHT SESSIONS — BUT NOT FOR THE REASON
  ITS REGISTER CLAIMED, AND ITS OPTIMUM SITS AT THE GRID BOUNDARY; SECTOR-NEUTRAL IS NOW FINISHED
  IN EVERY FORM (2026-08-12, session 35, `S14`+`S15`).** One register for both,
  `PREREG_s14_s15_band_sectorvalue.md`, committed **alone at `32051c0`**. **ADOPTS NOTHING.**
  * **`S14` IS ADOPT-ELIGIBLE, IN BOTH DIRECTIONS.** Sweeping the shipped width grid on the
    **decide** half and measuring the argmax on the **held-out** half, both directions pick width
    **0.30** and both clear: net alpha **+1.78pp / +1.77pp**, gross alpha **+1.02pp / +0.77pp**,
    measured cost saving **+0.76pp / +1.00pp**. **Turnover roughly HALVES** (2.6078 → 1.3514 and
    2.5800 → 1.4198) and the measured drag falls 0.0227 → 0.0126 and 0.0182 → 0.0106.
  * **CORRECTION TO MY OWN REGISTER #1, AND IT CHANGES WHAT THE RESULT MEANS: THE "PURE COST
    MECHANISM, NO SIGNAL CLAIM" FRAMING IS WRONG.** **Gross alpha IMPROVES**, so roughly **half**
    the gain is a *signal* effect, not a cost saving — holding a name until it leaves the top 30%
    rather than the top 10% stops the book churning on rank noise. That is a construction change
    with a real return consequence, and it means the audit's category-error argument (don't apply
    a signal margin to a mechanical saving) is only **half** applicable.
  * **CORRECTION #2: MY INDICTMENT OF THE AUDIT'S 1.5pp ALLOWANCE WAS TOO STRONG.** The register
    computed the saving at ~26 bps from the audit's quoted turnover and called the allowance **6×**
    wider than the prize. **The measured saving is 76–100 bps**, so it is ~**1.5×**. Tightening the
    guard was still right and the arm passes either way, but the magnitude asserted before the run
    was wrong.
  * **THE CAVEAT THAT MUST TRAVEL WITH THE VERDICT: THE ARGMAX IS AT THE GRID BOUNDARY IN BOTH
    DIRECTIONS.** 0.30 is the widest width the shipped grid contains and it won both times, so
    **the optimum is at or beyond the edge and the knee is NOT identified** — the selected width is
    an artefact of where the grid stops. **A wider grid is the obvious next test, not an
    adoption.** **C6 confirms the audit's noise warning**: the net-alpha surface is monotone on the
    early half and **not** on the late, where 0.20 dips below 0.15.
  * **A MECHANISM THAT SUPPORTS IT: S22 measured that top-decile alpha is still accruing at two
    years while a name typically stays in the decile for ONE rebalance.** A wider band harvests
    persistence the incumbent's tight exit throws away — the direction S22 pointed at and declined
    to test. **Recorded ELIGIBLE, not adopted** (a vintage event, and Don's call); **1 of 2 sibling
    arms**, though stronger than that label implies since it cleared **both** halves in **both**
    directions. **The band is ALREADY LIVE in the `taxable` configuration**, so an adopt would
    change the *default*, not introduce it. **B13 is only PARTIAL**, so "the book is investable"
    holds for the categorical screen and **not** the liquidity one.
  * **`S15` IS REJECTED AND ESSENTIALLY INERT — AND WITH IT, SECTOR-NEUTRAL IS FINISHED IN EVERY
    FORM.** `SECTOR-NEUTRAL-B6` named exactly two routes back: **`S25`** (closed **UNOBTAINABLE**
    in session 29) and **`S15`** (rejected here). **Both are shut.** Measured: Δalpha −0.01pp /
    −0.36pp, rank correlation **0.9879**, only **5 of 25** top names changed.
  * **CONTROL C4 IS EXACT AND IS WHAT MAKES S15 THE NARROW EXPERIMENT IT CLAIMS TO BE: every
    NON-value theme comes back BIT-IDENTICAL at max |Δ| 0.000e+00**, while `value` moves by
    1.5568. It moves the book **less** than the broad version did (0.9879 vs B6's 0.9836), as
    pre-registered. The buy-*t*-sell-alpha flag **did** fire on the late half — predicted at 55/45
    that it would not — but at −0.36pp for +0.037 of *t*, **inert describes it better than
    trade-off**.
  * **THE STANDING SECTOR CAVEAT NOW HAS NO REMEDY.** TICKERS supplies **today's** sector applied
    to 1998 rows; `S25` was the item that would have fixed it and it is closed. **Any future
    sector-aware result on this panel inherits a look-ahead that cannot be repaired on data we
    own.** **Equity `N` 183 → 185.** Expectations **4 right, 3 wrong** — the worst score in these
    sessions, and informative for it: both consequential misses are on S14, predicted to fail.
    `data/free_analysis/S14_S15.json`; `HANDOFF_edge_audit.md` §1-8.
- **THE HORIZON ENSEMBLE BUYS A REAL TURNOVER REDUCTION AT 11× TO 23× ITS OWN COST, AND THE
  BUCKET ARM MISSES BY 18 BASIS POINTS (2026-08-12, session 34, `S11`+`S12`).** One register for
  both, `PREREG_s11_s12_horizon_bucket.md`, committed **alone at `d867fe3`**. **ADOPTS NOTHING.**
  * **S11's PRIOR WAS REAL AND IS RECORDED: S22 measured the out-of-sample rank IC RISING with
    horizon (+0.034 → ~+0.072).** The counter-prior won anyway. **REJECTED in both halves and by
    the widest margin of the three arms** — Δalpha **−4.22pp / −2.05pp**, Δ*t* −2.353 / −0.927 —
    and the long-short leg moved against it **exactly as pre-registered**, because S22 had already
    measured that the persistence lives entirely in the long leg while the spread's HAC *t*
    collapses 2.7167 → 0.6846.
  * **THE AUDIT'S SECONDARY CLAIM IS CONFIRMED AND IS THE MOST USEFUL NUMBER HERE — AND IT IS A
    TERRIBLE TRADE.** Turnover falls **0.6352 → 0.4976** per rebalance, ~55pp of book per year.
    **At the project's own measured 33.4 bps one-way that saves roughly 18 bps/yr against 205–422
    bps of alpha given up — the trade runs 11× to 23× AGAINST.**
  * **C6 CONFIRMS THE COUNTER-PRIOR DIRECTLY: the two horizons' weight vectors correlate +0.9013
    and +0.9674**, so the ensemble is largely **one composite twice**. **A CONFOUND NAMED
    HONESTLY:** the blend's rank correlation against the *deployed* composite is only **0.6939**
    while the two horizons agree above 0.90 — so most of the arm's deviation comes from using
    **IC-proportional weights at all**, one of the eight schemes CPCV has always declined, not
    from blending horizons. The audit's own construction makes that unavoidable, since two
    flat-weighted composites would be identical.
  * **A SCOPE DIVERGENCE ON S12, NAMED BEFORE ANY RESULT (S10's class).** The audit's S12 is the
    **VALUATION bucket** — *"defined by how a name is valued, not by industry"* — while the task
    framed it as the **cap tier**. **Both tested as separate arms**, so the row closes on both
    readings and neither is reported as the other.
  * **A2 (VALUATION BUCKET) IS NOT_REPLICATED AND IS THE CLOSEST ANY ARM HAS COME IN THESE
    SESSIONS.** Positive on alpha in **both** halves (**+1.36pp / +0.82pp**) and positive on Δ*t*
    in both (**+0.478 / +0.347**) — it fails only because the late half misses the pre-committed
    +1.00pp bar **by 18 basis points**. **That is S21's shape exactly** (which missed by 17bps and
    was recorded not-replicated); ambiguous against a pre-committed threshold is a **NULL**
    (`RUN_RULES` A6), and it is **1 of 3 sibling arms**. Small intervention — rank corr 0.9807,
    top-25 changed 4 of 25. **NOT eligible, NOT adopted, and +1.36pp may not be quoted without
    both labels.** **The fourth consecutive session in which exactly one arm clears exactly one
    half.**
  * **A3 (CAP TIER) IS REJECTED AND NEARLY INERT** — Δalpha +0.09pp / +0.07pp. **C8 confirms the
    pre-registered mechanism**: the book's mean `size` z-score falls **0.5885 → 0.5092 (13.5%
    shrink)**, so it does neutralise the exposure X3 says carries the composite's entire
    significance — **but the alpha effect is ZERO rather than negative**, so it fails by being
    inert rather than harmful, a milder outcome than predicted.
  * **THE AUDIT'S OWN METRIC PRIORITY WAS ADOPTED VERBATIM** — *"top-decile alpha decides, not the
    t-statistic"* — and **no arm triggered the bought-*t*-sold-alpha flag**, so sector-neutral's
    failure shape did **not** recur.
  * **A NEAR-MISS CAUGHT BEFORE THE BUILD AND PINNED:** `bucket` is derived **after** the granular
    standardisation, so a naive lookup by column name would have found nothing, done nothing, and
    still reported a verdict on **an arm that never ran**. **A CONTROL THAT DID NOT RUN, REPORTED
    AS SUCH:** C7's bucket half came back empty for the same reason (the diagnostic column emitted
    `None`); the **arms are unaffected**, and the number was recovered from the key-identical
    corrected panel — **established 1,312 / speculative 339 per date**, both substantial.
  * **Equity `N` 180 → 183.** Expectations **7 right, 0 wrong**.
    `data/free_analysis/S11_S12.json`; `HANDOFF_edge_audit.md` §1-8.
- **THE O-SERIES IS CLOSED — 26 OF 26 — AND THE LAST ITEM'S BEST ARM IS A NULL THAT CLEARED
  EVERY BAR BUT ONE (2026-08-12, session 32, `O14`).** `PREREG_o14_tickflow_signals.md` committed
  **ALONE at `ea48f6b`**. Frozen book, **no live code path changed, nothing adopted.**
  * **EVERY OPTIONS IDEA IN THE CATALOGUE HAS NOW BEEN TESTED.** The `O14` ledger row is `DONE`,
    so all 26 O-rows are `DONE` and none is open. The register's own void condition forbade saying
    this before the row flipped, which is why the three previous sessions each had to qualify it.
    **These were the studies the 4.72GB alert-day tick cache was collected FOR**, so its
    justification is now paid.
  * **`sweep_share` IS THE CLOSEST THIS PROGRAMME HAS COME TO A DISCOVERY AND IS STILL A NULL.**
    Full sample LS **−0.1390 at |t| 3.061 against its own permutation p95 of 1.952**, two-sided
    permutation **p 0.00249**, and **the ONLY arm of five to survive Benjamini–Hochberg**. Its sign
    is **stable across halves** (−0.1689, −0.1086) and negative means **high sweep share earns
    MORE** — the institutional-FOLLOW direction. **It is NULL because the LATE half misses its own
    bar, 1.7741 vs 1.9357**, while the early clears at 2.6443 vs 2.1740 — **and the late bar is the
    LOWER of the two, so this is not a bar artefact.** The both-halves rule was fixed before any
    number existed and is the only thing between this and a reported discovery. **The autopsy's
    record was 0 in 126 hypotheses twice; this is 0 in 131.**
  * **NO SIGN COULD BE DECLARED, SO EVERY ARM IS TWO-SIDED — the only options register where that
    is true, and the audit's own argument forces it.** Pan–Poteshman found buyer-initiated
    put/call ratios predict, **on proprietary data with participant identification**; Bryzgalova
    et al. found retail is **>60% of options volume and LOSES money**, making signed retail flow a
    **fade** candidate; **public tick data cannot separate the two populations.** Two-sided costs
    power and that is the honest price. A **sign-agreement clause between halves** does the work a
    declared sign would.
  * **THE OTHER FOUR ARMS ARE NOWHERE**: `signed_volume` +0.0324 at 0.658, `pc_flow_imbalance`
    −0.0106 at **0.256 — the smallest of the five**, refuting my own prediction that it would be
    the largest — `block_share` −0.0212 at 0.437, `unusual_volume` +0.0771 at 1.511, none clearing
    its p95 or BH.
  * **A DAILY CROSS-SECTION IS IMPOSSIBLE, so the sort is MONTHLY**: per date median 2 names, max
    17, **ZERO dates reach 20**; per month median 31, 89 of 118 months reach 20. The same
    structural fact that redirected O3/O4/O5 and O25.
  * **THE LOOK-AHEAD CONTROL REPRODUCES AN INDEPENDENT MEASUREMENT EXACTLY**: `entry_premium`
    against the **traded contract's** last prevailing ask reads **0.0233 over 3,827 rows — the same
    0.0233 session 26 measured with a different implementation.** Lee–Ready classified a median
    **98.54%** of eligible prints.
  * **THE ONE LEDGER ROW A HUMAN WROTE IS THE ONE THAT WAS RIGHT.** Six `src=auto` rows in this
    series claimed no audit section existed and **all six were wrong**; `O14`'s `src=human` row
    named precisely the gap this register closed.
  * **THREE DEFECTS IN MY OWN INSTRUMENT, all caught before any verdict.** `classify_side`
    **contradicted its own docstring** (Lee–Ready's tick test needs the previous *different* price;
    the first cut carried the immediately preceding one, leaving runs of identical mid-prints
    unclassified) — caught by the test written to pin it. **The look-ahead control first measured
    the wrong instrument entirely**, reading a meaningless 1.5746. Plus dead code. A 4.4× speedup
    was verified **inert** on bit-identical feature values.
  * **Options `N` 280 → 285**, one per arm. Expectations **4 right, 2 wrong**.
    `data/free_analysis/O14_TICKFLOW_SIGNALS.json`; `HANDOFF_optionsbot.md` §50-53.
- **A BOOK WITH POSITIVE PER-TRADE EXPECTANCY LOSES MONEY AT REALISTIC SIZING, AND THE REASON IS
  MEASURED: THE EDGE LIVES IN THE CROWDED WEEKS AND A CONCURRENCY CAP REFUSES EXACTLY THOSE
  (2026-08-12, session 31, `O11`+`O19`+`O22`+`O25`).** `PREREG_o11_o19_o22_o25_portfolio.md`
  committed **ALONE at `1203a85`**. Frozen book, **no live code path changed, nothing adopted.**
  * **THE O-SERIES IS NOT CLOSED, AND THE WORDING WAS FIXED BEFORE ANY RESULT EXISTED.** After this
    batch **25 of 26 O-rows are DONE**; **`O14` remains OPEN** — its collection is complete and its
    first analysis landed, but the **put/call and unusual-volume studies the tick cache was
    justified by are still untested.** The accurate sentence is *"this closes the last four OPEN
    audit HYPOTHESIS rows"*, not *"the O-series is closed"*.
  * **`O11`: THREE OF FOUR CELLS UNSURVIVABLE, THE FOURTH MARGINAL, NONE SURVIVABLE.** Max drawdown
    (full): $50k/conc10 **0.6710**, $50k/conc50 **0.7769**, $250k/conc10 0.3589, $250k/conc50
    0.5842. **THE HEADLINE CONFIRMS THE AUDIT'S OWN HYPOTHESIS: a book with +3.27%/trade POSITIVE
    expectancy ENDS AT $37,059 FROM $50,000 — a −25.9% total return — at a concurrency cap of 10.**
    *Per-trade expectancy and survivability are different questions and only the first had ever
    been measured here.*
  * **THE MECHANISM, MEASURED AND THE MOST PORTABLE THING IN THE BATCH: ALERTS CLUSTER AND THE EDGE
    LIVES IN THE CROWD.** Over 483 weeks (median 7 alerts, max 38), expectancy is **−4.51% in quiet
    weeks** and **+14.28% in weeks above the 90th percentile**, with **51.5% of trades in weeks of
    >10 alerts.** So a concurrency cap refuses trades **exactly when opportunity is richest** —
    1,677 of 3,870 skipped at cap 10 — which is why the constrained small book is loss-making
    rather than merely volatile. This is the audit's own third possibility, confirmed.
  * **`O19` NOT-AN-ARTEFACT, and it RAN FIRST BY MECHANISM: the O11 stage REFUSES to run without
    O19's artifact** and embeds its verdict — demonstrated by invoking it with the artifact absent.
    This repairs session 26's defect, where a gating control and its outcomes ran in one pass.
    Equal +3.270%, contract-weighted +3.407%, dollar-weighted +3.141% — same sign, 0.27pp apart;
    premium floors move expectancy by 0.10pp. **The audit's premise barely applies here: the median
    position is THREE contracts, not twenty, because median premium is $2.57.**
  * **`O22` CAPACITY ≈ $76.6M ON THE REGISTERED MEASURE — AND IT MAY NOT BE COMPARED WITH P1's
    EQUITY $23M, FOR A MEASURED REASON: OPEN INTEREST IS A STOCK, ADV IS A FLOW.** The traded
    contract's daily volume is a median **0.1326** of its open interest (179 traded vs 1,373
    outstanding), so an OI-based capacity **overstates a flow-based one by ~7.5×** — flow-equivalent
    near **$10M**. **The registered headline stands as measured** (swapping the depth measure after
    reading the number is what the void conditions forbid) and the correction is reported beside it.
    Upper bound, λ is an assumption, and **mechanical rather than a recommendation** given R2.
  * **`O25` NULL ON BOTH ARMS, AND NOT MARGINALLY — THE WING IS RELIABLY WORSE.** At +75%
    (n 1,332) **−9.34pp vs closing and −9.69pp vs holding**; at +100% (n 1,082) **−13.03pp and
    −7.76pp** — negative in **both halves against both comparators, every CI excluding zero.**
    **The audit's own prediction is confirmed:** sd falls 0.823 → 0.707 and the share above +100%
    falls **74.2% → 56.6%**. Free by-product, no verdict: at +100% **closing BEATS holding by
    5.3pp**.
  * **THE SPLIT GUARD IS NOW SHARED AND RAISES**, as instructed after session 30's recurrence:
    `portfolio_capacity.assert_raw_spot` runs before any instrument touches a price, **raises
    rather than warns, and also raises when it can check nothing** (an empty overlap reporting
    success is the same failure in a new costume). It read **3,870 entries at median relative error
    0.00e+00**; six tests pin it and downgrading it is a void condition.
  * **THE LEDGER WAS WRONG ABOUT ALL FOUR ROWS — the third session running.** All four were
    `src=auto` / *"no mention anywhere in the corpus"*; the audit has full sections at `:1066`,
    `:1985`, `:2023`, `:2061`. **That note is not evidence of absence.** All four corrected.
  * **Options `N` 271 → 280** (2+4+1+2, exactly as pre-committed); equity and infra untouched by
    this item. Expectations **4 right, 2 wrong, 2 split**.
    `data/free_analysis/O11_O19_O22_O25_PORTFOLIO.json`, `O19_SIZING_ARTEFACT.json`;
    `HANDOFF_optionsbot.md` §46-49.
- **13F STALENESS IS COMMON ACROSS NAMES, NOT CROSS-SECTIONAL — SO DECAYING IT CANNOT RE-RANK
  ANYTHING — AND THE FRESHNESS GRADIENT THE WHOLE ITEM RESTS ON IS ABSENT
  (2026-08-12, session 33, `S8`+`S9`).** One register for both,
  `PREREG_s8_s9_freshness.md`, committed **alone at `b7804d8`**. **ADOPTS NOTHING.**
  * **THE STRUCTURAL FINDING, AND IT KILLS S8's 13F LEG OUTRIGHT: `days_since_13f` takes a mean of
    1.25 DISTINCT VALUES PER DATE** (median within-date sd **2.054 days**), because 13F
    quarter-ends are **common calendar dates** — at any rebalance every name's 13F is the same
    age. Its decay multiplier spans p05 **0.5163** to p95 **0.5427** with a **within-date sd of
    0.00587**, so the arm is not a staleness adjustment at all but a **uniform ~0.54×
    down-weighting of `institutional`** — a weight change, and the weighting family was rejected
    wholesale last session. Its rank correlation is **0.9880**, nearly inert.
  * **THE AUDIT'S PREMISE CONFLATES TWO DECAYS.** The 13F signal genuinely decays as the quarter
    ages — that is measured and real (alive Q−2 at *t* 1.36, dead Q−3 at −0.04) — but that is a
    **TIME-SERIES** decay common to every name, **not a CROSS-SECTIONAL one that could re-rank
    them.** By contrast `days_since_filing` takes **86.81 distinct values per date** (within-date
    sd ≈ 39 days), so the fundamental arm is a genuine cross-sectional variable.
  * **THE S9 DIAGNOSTIC IS THE RESULT, AND IT REFUTES THE PREMISE.** Top-decile forward return by
    filing-age quartile: **Q1 +6.15%@38d, Q2 +6.12%@66d, Q3 +6.66%@71d, Q4 +6.35%@88d.** **Not
    monotone**, whole spread ~half a point on a 6.3% base, and **Q1−Q4 = −0.78%/yr — the STALEST
    quartile very slightly outperformed the freshest.**
  * **MY REGISTERED LEAN WAS WRONG, IN THE INFORMATIVE DIRECTION.** The register was asked to
    state a lean and did: **the gradient is real, the weighted arms fail.** The weighted arms did
    fail — **but the gradient is not there either**, so both halves of the lean pointed at
    something in freshness and there is nothing.
  * **VERDICTS: all four REJECTED.** A2 freshness-as-input +0.61pp/−1.61pp; **A3 fundamental decay
    (90d) NOT_REPLICATED — late half alone at +1.73pp, Δ*t* +0.710, early −0.22pp**; A4 13F decay
    +0.03pp/−1.03pp; A5 combined −0.16pp/+0.41pp, landing **between A3 and A4 exactly as
    pre-registered**. A3 is **the THIRD CONSECUTIVE SESSION in which exactly one arm clears
    exactly one half** — the family-wise clause has now earned its keep three times. **1 of 4
    siblings, not eligible, not adopted.**
  * **C6 CONFIRMS THE PRE-REGISTERED CAVEAT: the freshness quartiles differ materially by
    sector**, largest fresh-vs-stale gap **Consumer Cyclical at 15.62pp** — fiscal year-ends
    cluster by industry, so any gradient would have been partly compositional (U7's failure mode,
    and S10's). Moot here since there is no gradient, but it binds on any re-opening.
  * **NO HALF-LIFE WAS FITTED** — 90d for fundamentals (a labelled convention), 180d for 13F from
    the project's own measured decay. Fitting on this panel then scoring on it is the in-sample
    selection already paid for (+8.43%/yr in-search → −0.04%/yr locked hold-out). **C5: zero
    negative ages**, which would have been look-ahead; **C7: the fundamental decay bites hard**
    (mean multiplier 0.4894), so A3's failure is not an inert-multiplier artefact.
  * **A DEFECT REPORTED, NOT FIXED: `bulk.prepare_daily` down-samples DAILY to ONE ROW PER
    TICKER-MONTH**, so the point-in-time market cap and the re-priced EV equity leg can be **up to
    31 days stale** while the price feeding `_price_factors` is same-day. Its docstring keeps the
    last date actually present and never a future one, so this is a **precision** defect, not a
    correctness one — and fixing it moves `size`, every EV-based ratio and the published headline,
    which needs its own register.
  * **TWO ARGUMENTS THAT LOOK SUPPORTIVE AND ARE NOT THE SAME HYPOTHESIS, separated in the
    register before running:** P6's *"recency beats smoothing"* (quarterly ROE beat TTM) is about
    the **WINDOW** a number is measured over, not the **AGE** of the observation — a quarterly
    figure filed 89 days ago is still quarterly; and **S27**, rejected last session, weighted
    **dates**, while these weight **names within a date**. **Equity `N` 176 → 180.** Expectations
    **6 right, 1 wrong**. `data/free_analysis/S8_S9_FRESHNESS.json`;
    `HANDOFF_edge_audit.md` §1-7.
- **THE SPLIT-ADJUSTED-SPOT DEFECT (U1-SPLIT'S CLASS) RECURRED IN A NEW INSTRUMENT AND WAS CAUGHT
  ONLY BY DISBELIEVING A NUMBER — READ THIS BEFORE MATCHING ANY STRIKE AGAINST A PRICE
  (2026-08-12, session 30, `O6`+`O7`+`O17`).** All ten arms NULL; two failed on exactly one
  pre-committed leg. `PREREG_o6_o7_o17_earnings_surface.md` committed **ALONE at `779d42c`**.
  Frozen book, **no live code path changed, nothing adopted.**
  * **THE DEFECT, AND IT IS THE MOST TRANSFERABLE THING HERE. Option chains are as-traded and
    UNADJUSTED; `data/bulk/prepared/bars`'s `close` is split- AND dividend-adjusted — NVDA in 2012
    reads 0.27 against a raw 11.97, a 43× ratio.** Matching an as-traded strike against an adjusted
    spot picks a contract nowhere near the money and **fails SILENTLY** — the option still prices,
    it is simply mostly intrinsic. **Measured against the book's own `underlying_entry` on 1,173
    banked entries: `raw_close` agrees EXACTLY (median rel err 0.00000, nothing >5% off) while
    `close` is off by a median 10.3% and by >5% on 67% of entries.** **RULE: `raw_close` for
    anything touching a STRIKE, `close` only for a RETURN.** My first cut reported a mean implied
    move of **19.57%** against a realised 5.26% and a confident RICH verdict — an **artefact**
    (2.82% of events >20% from the money, up to 30×). Repaired, coverage rose 0.2738 → 0.4459 and
    the implied move fell to a credible **5.45%**. **Anything else in this project matching a
    strike against `close` is suspect.** Pinned by three tests; a control that must stay empty
    reads ZERO.
  * **THE LEDGER WAS WRONG ABOUT TWO OF THE THREE ROWS**, both `src=auto`: O6 read *"prose mentions
    only, no section"* and O17 *"no mention anywhere in the corpus"*, yet `VALQUO_EDGE_AUDIT.md:964`
    and `:1150` are full sections naming four rules each. **Definitions were QUOTED, not invented.**
  * **`O6` ALL FOUR NULL, AND THE STRONGEST NUMBER IS THE CONTROL: the random-alternative-contract
    p95 is about −11.3pp/trade, so the mechanical 35-delta rule the audit wanted replaced ALREADY
    BEATS ARBITRARY IN-BAND SELECTION BY ~11 POINTS.** Gains: A1 lowest-IV **+0.074pp**, A2 IV-rank
    **−3.505pp**, A3 smile-residual **−11.099pp**, A4 vega/spread **+0.464pp**. **A3 is the audit's
    OWN headline suggestion (ORATS smoothed market value) and is the worst arm in the register.**
    **A4 is the near miss** — positive in both halves, clears both p95s, **NULL only on the audit's
    tail-concentration clause.**
  * **WHY THEY FAIL, AND IT INVALIDATES THE AUDIT'S FRAMING: the cheapness rules CHANGE THE DELTA
    rather than repricing a fixed trade.** Mean |delta gap| 0.004 / 0.248 / **0.310** / 0.125, A3
    drifting 0.374 → **0.458**. The audit claims this *"cleanly separates which NAME from which
    CONTRACT"*; on this candidate set **it cannot** — a cheapness criterion moves the exposure too.
    **A1's 0.004 gap means it is essentially the incumbent, so its null is near-tautological.**
  * **PORTABLE, from the zero-cost random-entry control arm: the same four rules reproduce the same
    ordering and magnitudes on the CONTROL book** (+0.057, −4.140, −9.382, +0.310pp over 5,984
    events). **This is contract selection generally, not the dead alert days** — so it carries to
    any future book.
  * **`O7`: EARNINGS OPTIONS ARE *RICH* ON THIS UNIVERSE, CONTRADICTING GAO–XING–ZHANG'S PUBLISHED
    SIGN.** Implied move **5.4512%** vs realised **4.7773%**, difference **−0.6739pp** (CI95
    [−0.8475, −0.5070], excludes zero); realised exceeds implied on only **35.07%** of events.
    Stated as universe-specific, not a refutation — their effect is strongest in **small** firms
    and this book has none. **The backtest is dead: −10.34% per straddle net of four crossings,
    negative in both halves.** A **declared deviation**: B2's registered non-announcement null was
    NOT computed, because it fails positivity in both halves and no null could change the
    conjunction.
  * **`O17`: AVOIDING EARNINGS GETS MONOTONICALLY WORSE** (+0.797 → −0.479 → −1.429pp at 5/10/15
    days, none clearing its null) — **the loser autopsy's IV-crush hypothesis is not merely
    unsupported, the data points the other way.** **C4 OWN-THE-EVENT fails on ONE leg only: gain
    +4.686pp/trade, POSITIVE IN BOTH HALVES (+5.748, +3.730) and CLEARING ITS NULL IN BOTH (+3.241,
    +2.941) — NULL solely because retention is 0.5706 against the pre-committed 0.70 floor.** The
    floor was fixed first and is **reported, not relaxed to fit**.
  * **THE CONFOUND THAT SHOULD HAVE KILLED C4 IS REFUTED BY MEASUREMENT.** Owning the event selects
    longer-dated contracts and O13 found expectancy climbs with tenor, so C4 could have been a
    **DTE filter wearing an earnings filter's name** (U7/S10's mode). It is not: DTE 60.0 kept vs
    56.4 refused, and **within every DTE quartile the gain stays positive** (+6.416, +6.310, +2.138,
    +2.711pp). Tenor independently reconfirms O13 (+0.376, −0.877, +6.736, +8.584pp by quartile).
  * **EARNINGS COVERAGE IS BETTER THAN `bulk.py` SAYS AND ITS HOLE IS SYSTEMATIC.** That file warns
    ~2.83 code-22 dates per ticker-year; on these megacaps it is **median 3.96 / mean 4.14**. But
    **29 of 186 names have ZERO coverage (388 trades, 10.0%) and EVERY ONE is a foreign private
    issuer** filing 20-F/6-K. **A filter reading "no date" as "no announcement" FAILS OPEN on a
    non-random tenth of the book** — the mode this lane refused once before. `refuse_within` returns
    **`None` for UNKNOWN** and callers must drop; four tests pin it.
  * **Options `N` 261 → 271** (4+2+4, exactly as pre-committed); **equity untouched BY THIS ITEM,
    though it reads 176 after the merge** (other lanes landed 15 equity trials the same day) —
    **re-read `by_domain` after merging rather than quoting a figure measured mid-session.**
    Expectations **6 right, 1 wrong**. `data/free_analysis/O6_O7_O17_EARNINGS.json`;
    `HANDOFF_optionsbot.md` §42-45.
- **EVERY PRE-REGISTERED INTERACTION IS REJECTED, ONE OF THE AUDIT'S FOUR CANNOT BE BUILT AT ALL,
  AND A CROWDING EXCLUSION MAKES DRAWDOWN WORSE — INDEPENDENTLY REPLICATING S10
  (2026-08-12, session 32, `S7`+`S18`).** One register for both,
  `PREREG_s7_s18_interactions.md`, committed **alone at `7fc6ab2`**. No panel rebuild — every
  input was already banked. **ADOPTS NOTHING.**
  * **`size × liquidity` IS NOT BUILDABLE, AND IS REPORTED RATHER THAN PROXIED.** The audit names
    four interactions; this one needs a liquidity measure and **there is none on this path** — the
    price export carries **date and close only**, so `avg_dollar_volume` cannot be computed in the
    panel at all (audit **B13**, whose ledger row was corrected last session to
    `PARTIAL — BLOCKED ON DATA` for this reason). **A market-cap or price stand-in would be a
    different hypothesis wearing this one's name**, and a test pins that no such proxy appeared.
    It charges **no trial**.
  * **SHORT INTEREST DOES NOT REACH HALF THE PANEL, AND THE MEASURED NUMBER IS NOT THE AUDIT'S.**
    The cache is real (48,539 tickers, 3,866,270 records, 2018-01-27 → 2026-07-30) but the audit
    says 40% of dates and it measures **32 of 69, 46.4%**, first covered **2018-04-20**, row
    coverage on covered dates **0.9269**. **Every covered date is in the LATE portion of a panel
    starting 2009-01-15, so S18 CANNOT satisfy a both-halves gate on the full panel** — an
    impossibility, not a power caveat. The register fixed the replacement first: S18's arms are
    gated on halves of the **covered subsample — 32 dates, 16 per half**, which is exactly
    `min_dates=16`, the thinnest split the shipped gate accepts. **A pass on 16-date halves is not
    the same object as a pass on 34-date halves.**
  * **ALL SIX TESTABLE ARMS REJECTED.** `value × quality` −1.17pp/−0.84pp; `momentum × vol
    regime` −0.48pp/−0.19pp; `value × institutional` −0.05pp/−1.09pp (coverage 0.7172, the
    handicap pre-registered); `value × short_interest` −0.49pp/−0.86pp. **`momentum ×
    short_interest` is NOT_REPLICATED — it clears the LATE half alone (+1.85pp, Δ*t* +0.812) and
    fails the early (−2.39pp).** That is **the second consecutive session in which exactly one arm
    clears exactly one half**, so the family-wise labelling clause has now earned its keep twice:
    **1 of 6 sibling arms, not eligible, not adopted.**
  * **THE EXCLUSION ARM INDEPENDENTLY REPLICATES S10 ON A DIFFERENT CRITERION.** Dropping the top
    5% most-shorted removed 4.83% of top-decile rows and moved return +27.08% → +26.77%
    (−0.31pp), while **max drawdown went −0.2809 → −0.2863 — a gain of −0.5404pp, i.e. WORSE.**
    S10 found a *valuation-band* screen worsened drawdown by 2.61pp and 3.35pp; a *crowding*
    screen worsens it too, same direction, smaller size. S10's caveats travel verbatim:
    `max_drawdown` is **negative** so the gain is `arm − base` (pinned by a test carrying the real
    measured pair), and **X7 calibrates no drawdown floor**, so this is a measurement carrying no
    verdict.
  * **THE AUDIT'S BONFERRONI PRESCRIPTION WAS DECLINED EXPLICITLY, WITH THE REASON REGISTERED
    FIRST.** It asks for *p* < 0.0125; **this project's gate is a MARGIN gate whose floors X7
    calibrated against a placebo**, and translating one into the other would invent an
    uncalibrated correspondence — the error X3 and session 10 both paid for. Multiplicity is
    honoured by **labelling** instead.
  * **CONTROL C7 IS THE CLEAN SURPRISE.** Adding an eighth input moves every theme's *relative*
    weight 1/7 → 1/8, so each arm is a **compound** change — registered in advance. Re-scoring
    with a **constant** eighth column isolates it: **+0.000173 and +0.000146 of alpha, essentially
    nil.** So the arms measure the interactions and nothing else. **This refutes the one
    expectation that missed** (I predicted the dilution would matter, 65/35).
  * **C5 zero point-in-time violations; C6 no interaction is a proxy for a parent** (largest
    |parent correlation| 0.4584). **Equity `N` 170 → 176.** Expectations **6 right, 1 wrong**.
    **Nothing was searched beyond the audit's named list** — searching the quadratic space is
    exactly what the tree combiner already did, and it *reversed* out of sample.
    `data/free_analysis/S7_S18_INTERACTIONS.json`; `HANDOFF_edge_audit.md` §1-6.
- **FIVE ALTERNATIVE WEIGHTING SCHEMES, ALL FIVE REJECTED — AND CPCV'S OWN BEST CHALLENGER MISSES
  ITS BAR BY A FACTOR OF SEVENTY-NINE (2026-08-12, session 31, `S5`+`S6`+`S13`+`S24`+`S27`).**
  ONE register for all five, `PREREG_s5_s6_s13_s24_s27_weighting.md`, committed **alone at
  `8b0917e`**. One panel build, six scorings on one frame. **ADOPTS NOTHING.**
  * **THE NUMBER TO REMEMBER, because it prices the whole family: CPCV's best challenger scheme
    (`positive-equal`) beat the deployed default by a margin of `0.000265` against a required bar
    of `0.020830` — it would have to be about 79× LARGER to clear.** `adopt=false`, PBO **0.80**.
    Weight tuning on this panel is not marginal; it is nowhere near.
  * **THREE OF THE FIVE PROPOSE BEHAVIOUR ALREADY SHIPPED, IN WHOLE OR IN PART** — all five rows
    were `src=auto`, and this is the S21 pattern for the third time. **`S27` is already shipped at
    the audit's own middle half-life**: `_theme_ic_stats` computes `0.5 ** (days_ago/halflife)`
    and **`halflife_days=1260` (≈5y) is the default of `_weighted_optimize`, `walk_forward` AND
    `cpcv_validate`**, while the audit proposes 3, 5 and 10. **`S5`'s shrinkage is half-shipped**
    as `ic-shrunk-50` (fixed 50% toward equal weight), already CPCV-rejected. **`S13`'s
    inverse-vol is shipped at the WRONG LEVEL** — `risk-parity` is inverse-vol across *themes*;
    S13 asks for it across *names*, a different object.
  * **VERDICTS.** `S5` REJECTED (−2.12pp / −1.68pp, rank corr 0.8933, shrinkage intensity
    **0.5641** so genuinely partial and not degenerate at either end). `S24` REJECTED and **very
    nearly the incumbent at rank corr 0.9907** — bagging a seven-signal set has almost nothing to
    bag. `S27` REJECTED at **both** half-lives by the widest margins of the five (−4.29pp / −2.98pp
    at 3y; −4.21pp / −2.66pp at 10y).
  * **`S6` IS THE ONLY ARM TO CLEAR ANY HALF, AND IT GETS THE FULL SKEPTICAL TREATMENT THE
    REGISTER FIXED IN ADVANCE.** Late half **+3.30pp at Δ*t* +0.678 — improves**; early half
    **−1.61pp at Δ*t* −1.289 — does not.** That is a sign flip between halves, this project's most
    repeated pattern, **and it is 1 OF 5 SIBLING ARMS**: five arms against one bar make
    at-least-one-clears roughly a **23%** event under independence. **NOT eligible, NOT adopted,
    and the +3.30pp may not be quoted without both labels.**
  * **`S13` FAILS THE ALPHA GATE WHILE IMPROVING EXACTLY WHAT IT EXISTS TO IMPROVE, AND THAT WAS
    REGISTERED AS AN INSTRUMENT MISMATCH RATHER THAN DISCOVERED.** Equal weight **+25.29%/yr,
    Sharpe 0.5866, maxDD −0.2809**; inverse-vol capped **+23.53%/yr, Sharpe 0.6261, maxDD
    −0.2804**. **Sharpe +0.0395 (≈6.7% relative), return −1.76pp, drawdown flat.** Its long-short
    leg is unchanged **by construction**, so its *t* margin is **N/A and may never be read as a
    pass**. X7 calibrates no floor for Sharpe, drawdown or turnover, so those carry no verdict.
    The drawdown barely moving is consistent with S10's finding that this book's maxDD is decided
    by one quarter (COVID 2020Q1).
  * **EXPECTATIONS SCORED 6 RIGHT, 0 WRONG — the first clean sweep in this record, and the reason
    matters more than the score.** The prior was not intuition; it was the project's own measured
    standing result — CPCV adopts nothing, the tree combiner **REVERSED** out of sample, and
    weight tuning went **+8.43%/yr in-search → −0.04%/yr on the locked hold-out**. **When the
    prior is a measurement, the calls stop being wrong.**
  * **A DEFECT IN MY OWN INSTRUMENT, resolved under the session-11 protocol.** The register's C5
    defines the reported intensity as the **shrinkage** intensity; the first cut of the code
    reported its **complement**, so the register's two degenerate ends read backwards against the
    implementation. Caught by the test written to pin it, before any verdict was read. **Proven
    presentational by diffing the pre-fix and post-fix artifacts leaf by leaf: the S5 weight
    vector is BIT-IDENTICAL (max |Δ| 0.000e+00) and ZERO gate cells moved on any arm in either
    half**, so no conclusion needed re-deriving. The register is left unedited; the code now
    matches it.
  * **A LIMITATION OF THE DESIGN AGAINST ITS OWN REGISTER, REPORTED NOT GLOSSED.** The register
    says CPCV is the authority "for every arm that produces a weight vector". **`cpcv_validate`
    selects among its OWN eight `_weight_schemes` and cannot evaluate an arbitrary vector**, so it
    does not bless or decline S5/S6/S27 individually; its authority operates here as a blanket
    keep-the-defaults rule, which is weaker than the register's wording implies.
  * **Equity `N` 165 → 170**, one trial per item. `data/free_analysis/S5_S6_S13_S24_S27.json`;
    `HANDOFF_edge_audit.md` §1-7.
- **SPLITTING NET ISSUANCE INTO TWO INPUTS CANNOT CHANGE AN ORDERING — IT IS A RANK IDENTITY,
  NOT A MEASUREMENT — AND BUYBACKS CARRY MORE OF THE THEME'S IC THAN DILUTION DOES
  (2026-08-12, session 30, `S16`).** `PREREG_s16_issuance_decomposition.md` committed **alone at
  `afc7578`**, a strict ancestor of the measurement commit. One panel build, five scorings, every
  arm a column on ONE frame. **ALL FOUR ARMS REJECTED. ADOPTS NOTHING.**
  * **THE PREMISE CHECK REMOVED HALF THE AUDIT'S METHOD BEFORE ANY ARM RAN.** All 671,417 ACTIONS
    rows carry one of nineteen action types and **NONE is a repurchase authorisation**, so
    buyback-announcement drift is **not testable on data we own**; and **`initiated` is
    index/security listing initiation** (its earliest rows are `^VIX`, `^RUT`, `^IXIC`, all
    1997-12-31), **not dividend initiation**. What IS there is `acquisitionof`/`acquisitionby` —
    8,248 dated rows each with deal values — which is the M&A leg. Same class as S25.
  * **THE DEEPEST FINDING IS AN IDENTITY, AND IT KILLS THE AUDIT'S ACTUAL PROPOSAL.** S16C's
    within-date rank correlation against the incumbent is **1.000000000000 on all 69 dates**,
    because `buyback = max(0, −net)` and `−dilution = −max(0, net)` are **both non-increasing in
    `net`** (verified directly on the real series), so the mean of their z-scores preserves the
    ordering of `neg_issuance = −net` **exactly**. **So "separate them into two inputs so the
    composite can weight them independently" cannot express any ordering the single input cannot
    — it only shrinks the theme's per-date dispersion 1.000315 → 0.774730, a 22.5% cut in
    effective weight.** The S20/S21 rank-invariance lesson in a new costume.
  * **BUYBACK CARRIES MORE OF THE IC THAN DILUTION, WHICH REFUTES TWO PRE-REGISTERED
    EXPECTATIONS.** Theme IC *t*: **S16A buyback-only +3.2066**, incumbent **+2.7530**, **S16B
    dilution-only +2.5623**. **S16A is the ONLY arm clearing X7's calibrated 2.71 theme-IC bar —
    and it still fails the gate**, which is the **fifth** demonstration that theme IC does not
    judge a construction change.
  * **VERDICTS: all four REJECTED** against the already-committed margins — S16A Δalpha
    +0.47pp / +0.05pp; S16B +0.23pp / −0.26pp; S16C +0.20pp / −0.06pp; S16D +0.17pp / −0.19pp.
    **S16D is FLAGGED DEGENERATE** by the pre-committed C6 rule (`mna_dilution` non-zero on only
    **3.19%** of rows) even though C7's own bar passed — the M&A flag fires on **5.53%** of
    dilution rows, inside the pre-registered 5–25% band.
  * **C3 DID NOT PASS ITS BAR AND IS REPORTED AS A FAILURE, NOT RECLASSIFIED.** The rebuilt
    incumbent differs from the shipped `capital_discipline` by up to **0.006676** (0.67% of one
    sd), because `build_frame` standardises over every scored name that date while the panel then
    drops names with no forward return. **Diagnosed, not asserted** — within-date rank correlation
    exactly **1.00000000**, median deviation exactly **0.000e+00**, a per-date affine rescaling
    with worst residual 1.0e-03 — **and bounded: re-running every gate against the SHIPPED column
    as baseline returns the same four rejects with deltas identical to four decimals.**
  * **ADOPTION WOULD COST MORE HERE THAN USUAL AND THE REGISTER SAID SO FIRST.** The current
    vintage is **DERIVED** per `PT-GAPDUE` — **vintage 3, opened 2026-08-11 — and its recorded
    reason IS the `capital_discipline` restoration.** So changing this theme's construction would
    close a vintage days old and open vintage 4, a second five-year clock reset on the same theme.
  * **Equity `N` 161 → 165**; options 258 untouched. Expectations **3 right, 3 wrong**. **NOT
    tested and named so it is not mistaken for tested:** buyback-announcement drift (no such data)
    and dividend-initiation drift (derivable, different signal, out of scope).
    `data/free_analysis/S16_ISSUANCE.json`; `HANDOFF_edge_audit.md` §2.
- **THE HEADLINE ALPHA IS NEGATIVE IN 29% OF QUARTERS, AND THE RESULTS FILE NOW SAYS SO
  (2026-08-12, session 30, `S28`).** Reporting infrastructure — **no hypothesis, no threshold, no
  verdict, and no published claim moves.** `statistics.distribution()` ships n, mean, sd,
  min/p05/p25/median/p75/p95/max, the count and fraction of **negative** periods, and the **dated**
  worst and best period, wired into four payload blocks (`construction.top_decile_alpha_
  distribution`, `construction.long_short_distribution`, `portfolio.return_distribution`,
  `portfolio.excess_vs_equal_weight_distribution`). `SCHEMA_VERSION` **5 → 6**, purely additive.
  * **WHAT IT SHOWS ON THE SHIPPED BOOK, which is why it was worth doing.** The published
    **+7.17%/yr** top-decile alpha is the mean of 69 quarterly draws of which **TWENTY ARE
    NEGATIVE (28.99%)**, with a **worst quarter of −6.83% (2016-01-20)** and a best of +11.47%
    (2022-07-22) — and a **median of +1.41% against a mean of +1.79%**, so the headline is
    **right-skewed and the typical quarter is worse than the average one**. The long-short spread
    is negative in **33.3%** of quarters, worst **−20.01% (2025-07-29)**.
  * **THE UNITS TRAVEL IN THE BLOCK, because the obvious misuse is annualising a quantile.**
    `top_decile_alpha` is periods-per-year × the **mean**; that scaling is a statement about a
    mean and **never about an order statistic**.
  * **CONSISTENCY IS ASSERTED, NOT ASSUMED: 4 × the distribution's mean reproduces
    `top_decile_alpha` to 4e-17** on the real panel and exactly on a synthetic one — the check
    that the block describes the SAME series the headline is a mean of. A distribution attached
    to the wrong series would look reasonable and quietly mislabel the worst quarter in the record.
  * **PINNED AS REPORTING-ONLY** by a test that fails if any threshold, gate or verdict ever
    compares or branches on a distribution field — **and that guard was checked for vacuity**: it
    inspects 14 code-level references, so it is not passing by seeing nothing. **Zero equity
    trials**; infra `N` 10 → 11 on the M2/M6 precedent, and infra `N` gates no published claim.
- **THE SURFACE-ANOMALY FAMILY IS NULL ON ALL THREE ARMS — AND THE PRIOR LANE'S ONE SUGGESTIVE
  RESULT REVERSES ITS SIGN ONCE THE INSTRUMENT IS FIXED (2026-08-12, session 29, `O3`+`O4`+`O5`).**
  One register, three arms, `PREREG_o3_o4_o5_surface.md` committed **ALONE at `d2aa5f9`** — one
  `.md`, zero `.py`. Frozen book, no re-mine, **no live code path changed, nothing adopted.**
  * **THIS IS A SECOND LOOK AT AN ALREADY-REJECTED HYPOTHESIS AND IS CHARGED AS ONE.** `64955ef`
    (now on `main`) tested all three characteristics with the published sign declared first and
    **REJECTED** them, and `HANDOFF_free_analysis.md` concluded they *"should be considered
    answered by that same run, not re-opened separately."* **The sole justification for re-opening
    is a deviation that lane declared itself and never closed:** it used a **straddle**, which is
    delta-neutral **only at inception**. This register changes the **INSTRUMENT** and nothing else
    that can be held fixed — A1 reuses that lane's own `idio_vol` values and the panel's own strike
    and expiry.
  * **THE POWER ARGUMENT HELD, WHICH IS THE ONLY REASON THE TRIALS WERE WORTH SPENDING: delta-hedged
    return dispersion is sd 0.0303 against the straddle's 0.9055 on the identical events — a 30-fold
    reduction**, and every arm's |t| rose against its straddle counterpart.
  * **ALL THREE NULL, EACH ON TWO INDEPENDENT LEGS.** `idio_vol` n 3,289, monotonicity −0.1717,
    LS *t* 2.5158 vs its **own permutation p95** 2.016; `exp_idio_skew` n 3,154, −0.0380, 1.9143 vs
    1.9229; `vol_of_vol` n 3,318, −0.0690, **2.9703 vs 1.9459 — the largest margin in the register
    and still NULL.** Monotonicity misses the 0.6 bar three- to fifteen-fold in **both halves of
    all three**, and the both-halves *t* leg fails separately — **the two arms that clear
    full-sample fail in OPPOSITE halves** (A1 late 1.1509, A3 early 1.8189). Session 7's LOO
    pattern again. **A2 misses its own bar by 0.0086 of a *t* and is recorded a NULL, not rounded
    into a pass** (`RUN_RULES` A6).
  * **THE FINDING IS THE SIGN REVERSAL, AND IT RETIRES A CLAIM RATHER THAN ADDING ONE.** On the
    straddle `idio_vol` sorted **+0.9 CONTRADICTING** the published sign (LS *t* −1.2142) — that
    lane's single most suggestive result. On the delta-hedged instrument the same characteristic on
    the same panel sorts in the **CONFIRMING** direction (+2.5158). **Both readings are now
    unquotable as settled:** this one is far too weak to clear, and the prior CONTRADICTS reading
    is an artefact of an instrument that lets the underlying's move dominate.
  * **THE INSTRUMENT BEHAVES AS THE LITERATURE SAYS, which is corroboration it is real rather than
    a bug:** mean delta-hedged gain **−0.0072** and **every quintile of every arm negative** — the
    volatility risk premium, reproduced without being targeted. Separately, `idio_vol` is **+0.8444**
    rank-correlated with ATM IV, so A1 is close to a **pure implied-vol sort**.
  * **THE FROZEN CHAINS NAMED IN THE TASK PROVABLY CANNOT DO THIS, MEASURED BEFORE THE REGISTER.**
    The freeze holds a full chain only on **ENTRY** dates: median **1** full-chain name per date,
    max 17, and **0 of 2,498 dates and 0 of 120 month-ends** reach the ~20 a quintile sort needs.
    The panel is the EOD chain cache instead — **a forced substitution, disclosed in §1 rather than
    quietly made.**
  * **A DIAGNOSTIC WITH NO VERDICT, AND BOTH OBVIOUS EXPLANATIONS ARE REFUTED: Q5 is the WORST
    bucket in ALL THREE arms while Q1–Q4 are unordered** — exactly how a significant long-short
    coexists with near-zero monotonicity. It is **not one effect three times** (`idio_vol` vs
    `vol_of_vol` rank-correlate **−0.2920**, Q5 overlap **14.0%**) and **not illiquidity** (the
    gradient runs in **opposite** directions — `idio_vol`'s Q5 is the most liquid corner,
    `vol_of_vol`'s the least). **Left OPEN for its own register; testing it here would be the fourth
    arm my own void condition 3 forbids.**
  * **A DEFECT OUTSIDE THIS LANE: in the prior lane's `panel.pkl`, `illiq` and `spread_pct` are THE
    SAME COLUMN, identical on all 3,373 rows.** Its `illiq` was **the only characteristic in that
    published run with |t| > 2 (2.46)** and is described as a mechanical liquidity control; it is
    the option's quoted spread percentage under a second name. **Reported, not repaired.**
  * **Options `N` 258 → 261** (one per arm, exactly as pre-committed); **equity untouched BY THIS
    ROW, though it now reads 161** — the `S3` lane landed three equity trials the same day, which
    is why an equity figure must be re-read after every merge rather than quoted from a session's
    own measurement. `BACKTEST_RESULTS.json` needs no re-run **for this item**; the `S3` lane
    already refreshed it at its own denominator. Expectations scored **4 right, 2 wrong** — the misses
    being the sign reversal and the fact that Boyer–Vorkink's **expected** skew is **stronger** than
    the realised version the prior lane used (1.9143 vs 1.5805).
    `data/free_analysis/O3_O4_O5_SURFACE.json`; `HANDOFF_optionsbot.md` §38-41.
- **ALL THREE INSIDER REBUILDS ARE REJECTED, AND THE AUDIT'S OWN THRESHOLD WOULD HAVE REJECTED
  THEM FOR A REASON UNRELATED TO WHAT THE COMPOSITE DID (2026-08-12, session 29, `S3`).**
  `PREREG_s3_insider_rebuild.md` was committed **alone at `b3a85fa`** — one `.md`, zero `.py`, a
  strict ancestor of the measurement commit. One panel build, four scorings, all arms columns on
  ONE frame so the row set is identical by construction. **ADOPTS NOTHING.**
  * **REJECTED on all three arms** against the already-committed margins (+0.25 long-short *t*
    AND +100bps top-decile alpha, BOTH halves, boundary embargoed, deployed flat 1/7, no grid):
    **S3A** (drop the `buys` bonus) Δalpha **+0.01pp / +0.79pp**, Δ*t* +0.116 / +0.110;
    **S3B** (scale by market cap) Δalpha **+0.82pp / +0.52pp**, Δ*t* +0.095 / +0.079;
    **S3C** (split into two z-scored inputs) Δalpha **−0.92pp / −1.24pp**, Δ*t* −0.332 / −0.120.
  * **THE UNUSUAL PART IS THE SIGN-STABILITY, AND IT CUTS BOTH WAYS.** Session 7's LOO pattern —
    arms flipping sign between halves — is this file's most repeated finding, recorded five
    times. **Here every arm is sign-stable on both metrics in both halves.** But the gains are
    far below the bar, and **V2G established there is NO CALIBRATED FLOOR for a paired
    within-panel difference**, so *"small but consistent"* is an observation, not a result.
  * **S3B IS THE BEST OF THE THREE, EXACTLY AS THE AUDIT PREDICTED** — the only arm with a
    positive theme IC (**+0.5763**) and the only one positive on alpha in both halves by more
    than a basis point. It is also the most different from the incumbent (within-date rank
    correlation **0.8721** against S3A's 0.9668). **It still does not clear.**
  * **THE AUDIT'S OWN BAR IS REFUTED AS AN INSTRUMENT, AND THE REGISTER DEMOTED IT IN ADVANCE.**
    Its threshold is *"theme IC t clears +1.0"*. **NO ARM CLEARS IT** — not even the two that
    improve alpha in both halves — **and neither does the shipped incumbent, at −0.2259.** So the
    audit's gate rejects all three for a reason unrelated to what the composite did, and +1.0
    sits far below **X7's calibrated 2.71** anyway. **Never judge a construction change by theme
    IC** — P6.3, X3, S20/S21, and now this.
  * **THE MOST INTERESTING NUMBER IS THE AVAILABILITY DIAGNOSTIC, AND IT DOES NOT CONVICT.**
    `insider` is the only theme with a materially non-zero mean (**−0.1031**) at **83.1%**
    coverage, so a name that HAS an insider score takes a small systematic negative tilt a name
    without one does not — S10's data-availability failure mode. Measured: the pure indicator
    *"has an insider score at all"* carries median IC **+0.01345 at t +1.4471**, **NOT separable
    from zero**, so the artefact is **not demonstrated**. Reported because the indicator's |*t*|
    is **LARGER than the insider theme's own (−0.2259)**: the mere presence of filings carries
    more forward-return information than the score's direction does. **Neither is significant;
    the comparison is the point.**
  * **THREE PREMISE FINDINGS, all in the register before any arm ran.** (a) One of the audit's
    own S3 items — `searchsorted(..., "right")` making a same-day Form 4 usable — is **ALREADY
    FIXED by B26** and was not re-tested. (b) **The formula was DUPLICATED** at `:737` and
    `:800`; there is now one `_insider_formula` and both paths delegate, **proved bit-identical
    to both pre-refactor copies over 20,006 cases against git HEAD's own source**. (c) **MY OWN
    OPENING HYPOTHESIS WAS REFUTED BEFORE THE REGISTER WAS WRITTEN** — I expected the non-z-scored
    affine map to leave `insider` under-dispersed and so under-weighted; measured, its per-date
    sd is **0.9600 against 0.8296** averaged over the other six, about **116% of nominal**,
    because the **multi-input** themes are the compressed ones (`quality`, ten inputs, 0.50).
  * **CONTROLS: C1 reproduces the record to sixteen digits and the run ABORTS before reading any
    arm if it does not; C3 the incumbent rebuilt from the banked raw `(net, buys)` is
    bit-identical to the shipped column, max |Δ| 0.000e+00 over 94,660 rows; C6 coverage 0.8308
    IDENTICAL across all four arms**, so S3B's comparison is not partly a universe change.
  * **A DEFECT IN MY OWN FIRST CUT: it used `build_fundamental_panel`'s DEFAULT
    `lookback_years=6` and produced a 21-date / 2,151-name panel** — a **SMOKE TEST**, from which
    the METHODOLOGY RULE forbids a verdict. Re-run at the canonical
    `CONFIG.backtest_lookback_years=18`; the script now **asserts** the shape rather than warning.
  * **Equity `N` 158 → 161**, options 258 and infra 10 untouched. **Adoption would be a VINTAGE
    EVENT** — the current vintage is **DERIVED** per `PT-GAPDUE` (**vintage 3, opened
    2026-08-11**), so it would open vintage 4 — and no arm is eligible in any case. Expectations
    scored **5 right, 2 wrong**. **Zeroing `insider` is NOT re-opened as a fallback conclusion of
    this register**; that needs its own, with its own trial charge.
    `data/free_analysis/S3_INSIDER_REBUILD.json`; `HANDOFF_edge_audit.md` §2.
- **THE POINT-IN-TIME SECTOR MAP IS UNOBTAINABLE FROM ANYTHING WE OWN — AND THE LOOK-AHEAD REACHES
  THE POINT-IN-TIME *VALUATION*, NOT JUST THE REJECTED RANKING (2026-08-12, session 29, `S25`).**
  Closed as **UNOBTAINABLE-WITHOUT-NEW-DATA**. No register and **zero trials**: every finding is a
  fact about what data exists and what the code reads, not a hypothesis tested against a
  threshold (session 8's precedent).
  * **OBTAINABILITY, MEASURED.** The TICKERS snapshot carries six fields — `sector`, `industry`,
    `country`, `exchange`, `category`, `scale` — and **ZERO date fields**, so it cannot say *when*
    a classification took effect and cannot bound reclassification even for names it covers. SF1
    `fundamentals.csv` has **112 columns and no sector or SIC**; `bulk/actions|events|sf3|daily`
    carry none; no prepared cache holds a SIC; and `valuation/data/edgar.py` fetches only
    `company_tickers.json` and companyfacts XBRL, neither of which carries a historical SIC.
  * **THE SOURCE NAMED FOR THE D-SERIES: the EDGAR filing-header `ASSIGNED-SIC`**, which IS the
    classification as of the filing date (~1 fetch per filing, ~180k for this universe). **What
    does NOT work, because it is the obvious first try: `data.sec.gov/submissions/CIK*.json`
    carries only the CURRENT `sic`** — a second snapshot, not a history.
  * **A CONFOUND THAT MUST TRAVEL WITH ANY SUCH BUILD: SIC IS NOT THE SHIPPED TAXONOMY.** The
    panel's sector is an 11-value GICS-like string, so a SIC-derived map changes point-in-timeness
    **and** taxonomy at once and **cannot cleanly measure what reclassification changes**.
    Isolating that needs the SAME taxonomy at two dates — a historical GICS snapshot, not sold as
    history.
  * **THE FINDING THE LEDGER DID NOT HAVE.** The row said *"nothing currently rests on it because
    every sector result has rejected"* — true of the RANKING, **false of the VALUATION**.
    `calibration.py:523-527` passes **today's** TICKERS sector into `pit_company` for a 1998 or
    2009 valuation, where it selects `assumptions.SECTOR_TARGET_MARGIN` (**0.100 → 0.270, a 2.70×
    spread**) and `comps.SECTOR_MULTIPLES` (**PE 2.50×, EV/Sales 6.15×**). **S23's own code pins
    BETA point-in-time two lines below while passing today's sector straight through**, so S23's
    exit-rule arms and **S10's bull-case band** both inherit it. **Not repaired — there is no data
    to repair it with — but pinned by test so it cannot rot.**
  * **CONSEQUENCE: full sector-neutral ranking stays permanently closed.** `SECTOR-NEUTRAL-B6`
    named `S25` as one of only two routes back; that route is **shut until the D-series delivers
    the EDGAR map**. `S15` (sector-relative on the value theme alone) is untouched and remains the
    other. Nothing here affects the accepted `max_sector_w` cap. **A correction against my own
    probe: its first cut reported a date-like field on the snapshot — the regex alternation
    contained `to`, which matched "sec*to*r". There is none.** `HANDOFF_edge_audit.md` §1.
- **THE FORWARD TRACK'S RECORDING GUARD DEMANDED A ROW NOBODY COULD HAVE WRITTEN YET, SO
  `recording_ok` READ FALSE EVERY WEEKDAY MORNING — AND THE ONE READING THIS SESSION EXISTED TO
  TAKE RETURNS `None`, NOT A VERDICT (2026-08-12, session 28, `PT-GAPDUE`).** Sessions 15 and 16
  both set 2026-08-12 as the date `/api/track` → `contract_track.recording_ok` would finally
  settle `PT-WRITER`. It was read. **Neither predicted branch fired, `PT-WRITER` is NOT closed
  and NOT refuted, and the ledger row stays `BLOCKED`.**
  * **THE CLOCK MOVED UNDER THE PREDICTION, AND THIS IS THE PART EVERY LANE MUST PICK UP: the
    bound inception is 2026-08-11 and the operational gate is 2027-02-11** *(**SUPERSEDED
    2026-08-14: vintage 4 opened 2026-08-13 on Don's S14 adoption, so the live figures are
    inception 2026-08-13 and gate 2027-02-13. Kept as the record of what vintage 3 was — and as
    the third demonstration in four days that a hard-coded vintage date rots within days. DERIVE
    it from `track_meter.VINTAGES`; never quote one from this file.*)*, not the 2026-08-10 /
    2027-02-10 this file and the ledger both still assumed. The theme-restoration lane closed
    vintage 2 and opened **vintage 3** on 2026-08-11 (capital_discipline reaching a live score is
    an ADOPTED change), so **vintage 2 lasted ONE DAY** and vintage 3's first row is not owed
    until **2026-08-13**. `recording_ok` is therefore `None` — the contract's own
    not-vacuously-green rule working correctly, since no trading day is yet due. **Derive the
    vintage, never quote it from a prompt or a handoff.**
  * **A DEFECT IN THE INSTRUMENT, MINE, AND IT MADE EVERY PREVIOUS MORNING'S READING
    MEANINGLESS.** `gap_report` counted the CURRENT day as due from midnight, but a trading day's
    row is written after that day's close. **Measured: a writer holding every row it could
    possibly have written still read `recording_ok: false` on 11 of 11 replayed trading-day
    mornings, always naming the current day.** That is the exact mirror of the vacuous-PASS
    defect session 15 caught in this same function, and since **LA8 put the gap on PUBLIC
    surfaces** it was a daily false alarm on a red light that is supposed to be loud. A row now
    falls due at the start of the **next trading day**, keyed to the calendar and deliberately
    NOT to the writer's 20:01 cron — hard-coding a clock time would couple the contract's gate to
    one implementation's schedule. Detection is delayed by at most one trading day, well inside
    the contract's own **LOGGED-NOT-VOIDED** allowance for a single day's write filled the same
    week.
  * **A CORRECTION AGAINST MY OWN FIRST CUT, kept because the error is the instructive part.** I
    first reported that vintage 2 owed a row for 2026-08-11 and never received it. **It owed
    NOTHING** — under the corrected rule that row does not fall due until 2026-08-12, and vintage
    2 had already closed. The claim was an artefact of **the very off-by-one the same change
    repairs**, computed with the old rule while arguing for the new one, and it was caught by the
    test written to pin it.
  * **A SECOND REAL DEFECT: A VINTAGE EVENT SILENTLY CLEARS THE RECORDING GAP.** `gap_report` is
    scoped to the open vintage, which is correct — the contract attaches the gate to the current
    vintage — but it means a dated miss stops being reported the moment the next vintage opens.
    **Vintage 1 owed six rows and got two, and its four missing dates (2026-08-03, -04, -05, -07)
    are unreachable from anything `recording_ok` reports today.** The contract tolerates a missed
    day as LOGGED-NOT-VOIDED, but **it can only be logged if something records it, and nothing
    did.** New `track_meter.recording_history` reports every vintage side by side and reproduces
    the contract's own 2-of-6 figure; **`recording_ok` is deliberately unchanged.**
  * **ON THE WRITER ITSELF — EVIDENCE, NOT PROOF, AND THE SESSION'S OWN HYPOTHESIS IS REFUTED.**
    The bound `data/valquo_track_history.csv` has mtime **2026-08-07 18:07** and was untouched
    across **both** 2026-08-10 and 2026-08-11; no scheduled task matching the reported name
    exists; and no code in this repository writes the file (session 13's finding, still true).
    **The "the write died in the overnight restart" hypothesis is refuted by timing:** the
    machine restarted at **03:33 on 2026-08-12**, which is **7.5 hours AFTER** the 20:01 window
    on 2026-08-11, so it cannot have interrupted that write. **And the local copy is not a stale
    mirror of a healthy remote** — the weekly `track-backup` cron pulled the LIVE service's bound
    Index on 2026-08-10 18:09 and committed the same two rows; `/api/track` is owner-only and
    returns 403 unauthenticated.
  * **ZERO TRIAL COST — a correctness repair, logged `FIXED`. Equity `N` stays 158**, options
    258, infra 10, and `BACKTEST_RESULTS.json` needs no re-run. **A near-miss worth carrying:
    `RESEARCH_LOG.md` holds TWO tables with DIFFERENT 9-column schemas, and an append lands under
    the SECOND** (`id|date|domain|pre|hypothesis|metric|verdict|n|source`). My first row used the
    first table's layout, so the parser could not find its verdict cell and **counted a `FIXED`
    repair as an infra trial**; caught by diffing `by_domain` against `HEAD` rather than by
    reading the row. `HANDOFF_edge_audit.md` §1-6.
- **THE DOWNSIDE-EXCLUSION SCREEN IS NOT MERELY INERT, IT IS COUNTERPRODUCTIVE — THE NAMES IT
  DELETES OUTPERFORM THE NAMES IT KEEPS AND CRASH AT HALF THE RATE (2026-08-11, session 27,
  `S10`).** Don's own question, formalised: *should a top-decile name whose point-in-time BULL
  case already sits at or below price make the book at all?* `PREREG_s10_downside_exclusion.md`
  was committed **alone at `a041e09`** — one `.md`, zero `.py` — a strict ancestor of the
  measurement commit. **ADOPTS NOTHING and no live code path changed.**
  * **THE SCOPE DIFFERS FROM THE AUDIT'S OWN S10, DELIBERATELY, AND THE REGISTER SAID SO BEFORE
    ANY RESULT.** `VALQUO_EDGE_AUDIT.md:739` specifies S10 as an **accounting red-flag veto** —
    Beneish M-score, Altman Z-score, external financing, NT late-filing notices. **This tested
    NONE of those four.** It ran the **valuation-band** exclusion instead. The ledger row is
    therefore **`PARTIAL`, not `DONE`**: *the accounting half has never been tested and closing
    the row would tell the next session it had been.*
  * **THE MECHANISM ARM IS THE FINDING, AND IT REFUTES THE PREMISE RATHER THAN FAILING A BAR.**
    Within the top decile the **flagged** names return **+6.5125%/63d** against the unflagged
    **+6.2677%** — the names the screen would delete very slightly **OUTPERFORM** the ones it
    keeps (**+0.98pp/yr, HAC *t* +0.4775**, a clean NULL that flips sign between halves at
    −0.41pp early and +2.12pp late). **There is no information in the flag in either direction.**
  * **THE AUDIT'S OWN KEY COUNT GOES THE WRONG WAY TOO.** Its argument is that an exclusion screen
    *"only needs to avoid a small number of catastrophic outcomes"*. Measured: flagged names fall
    more than 50% in **15 of 3,129 (0.479%)** against **69 of 8,297 (0.832%)** for the names
    retained. **The screen preferentially removes the names that crash LESS often, at roughly half
    the rate of the ones it keeps.**
  * **REJECTED on both arms, and drawdown does not merely fail to improve — it WORSENS.** Against
    the audit's asymmetric bar (drawdown better by >2.0pp AND alpha worse by <1.0pp, both halves):
    `A1 DROP` −2.61pp of drawdown and −0.24pp of alpha; `A2 BACKFILL` −3.35pp and −0.93pp, with
    the late half −2.14pp. The alpha effect **flips sign between halves** (helps early, hurts
    late) — session 7's LOO pattern for the fifth time.
  * **WHY, MEASURED ON THEME z-SCORES: the screen deletes the exposure R1 says is real.** Flagged
    names carry **higher momentum** (+0.9530 vs +0.6741) and **much lower value** (+0.2728 vs
    +0.7362, the largest move in the table). R1's re-run puts the book on **UMD +0.205 (t 3.65)**
    and **HML +0.251 (t 2.93)**, so a DCF-based bull case sits below price for exactly the names
    that have already run. The screen strips momentum and tilts the remainder further into value —
    the **FNMA value-trap direction** the free-analysis lane documented. Illustration, not
    evidence: on the last scored date the screen drops 8 of 25 names and **adds Freddie Mac and
    MBIA**.
  * **IT IS ALSO SUBSTANTIALLY A SECTOR EXCLUSION WEARING A VALUATION SCREEN'S NAME — U7's failure
    mode in a new costume.** The flagged **rate** runs **51.38%** for the financial valuation
    regime against **12.66%** for hypergrowth, and by sector **48.88%** for Financial Services and
    **40.32%** for Real Estate against **15.79%** for Industrials. A three-fold spread: much of
    what this "valuation screen" does is **hold fewer banks and REITs**.
  * **A DEFECT IN MY OWN INSTRUMENT, CAUGHT BEFORE ANY VERDICT WAS READ.** `max_drawdown` is
    **negative**, so an arm improves it by being **less** negative and the gain is `arm − base`.
    The first cut computed `base − arm` and **reported a 2.61pp WORSENING as a 2.61pp
    IMPROVEMENT** — it would have left the REJECT verdict standing while **inverting the reported
    reason for it**. This is the `monotonicity` sign error one lane over, and it is now pinned by
    a **known-bad fixture carrying the real measured pair**.
  * **THE DRAWDOWN LEG IS DECIDED BY ONE QUARTER, AND THAT IS MEASURED RATHER THAN ASSERTED.** The
    worst peak-to-trough spans **exactly ONE 63-day period on every arm**, at the same trough
    index **44 of 69** — COVID 2020Q1. The register called max drawdown *"a single order
    statistic"*; this is that caveat with a number on it. **X7 calibrates no drawdown floor
    anywhere**, so the 2.0pp bar is **UNCALIBRATED** and is labelled so.
  * **THE ALPHA LEG CANNOT RESOLVE ITS OWN BAR, AND THE REGISTER SAID SO FIRST.** The audit's
    1.0pp allowance sits **BELOW X7's calibrated 1.95pp** alpha margin *(**CORRECTED 2026-08-14,
    `MA19`: the calibrated margin is **1.8629pp** at `N` = 224, not 1.95pp — that figure was X7's
    at `N` = 84 and has been superseded since session 10. **The argument is unaffected and holds a
    fortiori**, since 1.0pp sits below both.)*. It survives only because
    it is a **non-inferiority** allowance, so **a pass means "no alpha loss detectable at this
    panel's resolution", NEVER "the loss is under 1pp"** — X3's error, named in advance.
  * **CONTROLS ALL PASS. C1 is the strong one: the rebuilt panel reproduces S23's banked
    fair-value panel on all 108,241 shared keys at `max |Δ| = 0.000e+00`** across twelve base
    fields, with `valuable`/`regime`/`method`/`growth_led` **100.000000% identical** — so adding
    the band did not disturb the base by a bit. **C2** the band **IMPORTS
    `pipeline._blend_scenarios`** rather than re-implementing it, so it is the same number the
    site renders as its scenario card (B7's defect class, pinned). **C3 ZERO** ordering violations
    of `bear ≤ base ≤ bull` over 108,100 full trios. **C5 the harness reproduces the published
    record to sixteen digits and the run ABORTS before reading any arm if it does not.**
  * **Coverage first, per the COVERAGE RULE: 11,426 top-decile rows, bull-case coverage 92.42%,
    flagged 27.38%.** A name with **no** computable bull case is **KEPT, never excluded** —
    excluding on missing data is a data-availability screen wearing a valuation screen's name,
    and it would correlate silently with era, domicile and regime.
  * **Equity `N` 155 → 158** (three arms — DROP, BACKFILL, MECHANISM — each of which could
    independently have been reported as a positive finding). Expectations scored **5 right, 1
    wrong**, unusually good here **and for a stated reason: they were derived from measured facts
    already in the record** (R1's UMD/HML loadings, the free-analysis down-quarter result) rather
    than from intuition. The one miss is the audit's premise itself — the screen was predicted to
    catch a non-trivial number of genuine disasters, and it catches them at **half** the rate of
    the names it retains. `data/free_analysis/S10_DOWNSIDE_EXCLUSION.json`;
    `HANDOFF_edge_audit.md` §1-5.
- **REAL TRADES PAY ABOUT TWO THIRDS OF THE QUOTED HALF-SPREAD, A PASSIVE FILL IS NOT A FREE
  HALF-SPREAD — AND BOTH ITEMS RETURN **NO VERDICT** BECAUSE MY OWN VOID CONDITION FIRED AND
  DISQUALIFIED THE ARM THAT WOULD HAVE CLEARED THE BAR (2026-08-11, session 26, `O10` + `O18`).**
  First use of O14's tick cache. `PREREG_o10_passive_fills.md` and `PREREG_o18_spread_cost.md` were
  committed **together and ALONE at `34b0c11`** — two `.md`, zero `.py`. Frozen book, no re-mine,
  **no live code path changed**.
  * **THE SCOPE FACTS WERE MEASURED BEFORE THE REGISTERS WERE WRITTEN, AND THEY RULE OUT THE
    QUESTION MOST PEOPLE WILL THINK WAS ANSWERED.** O14's cache is **exactly the alert-days and
    nothing else**: for the 3,870 banked entries the **next session is cached for 0 of 3,870 and
    the exit day for 0 of 3,870**. The live bot submits after the close and its order rests on
    **D+1**, so **"what the live bot's limit orders fill at" is NOT ANSWERABLE on this cache** and
    no verdict is issued about it. **Only the ENTRY leg is coverable while a round trip crosses the
    spread twice.** What *is* answerable is the execution environment of the exact contracts the
    book traded, measured **quote-relatively** — no decision time, no look-ahead. Join complete:
    **3,869 of 3,869**, the one missing day (`BUD` 2024-01-10) costing exactly one row.
  * **THE VOID IS THE HEADLINE AND IT IS NOT A TECHNICALITY.** C2 required the behavioural
    condition-code split to replicate; it failed on **one code** — code 35, 4.94% of prints, reads
    at-touch **0.2496** on the full book against **0.439** on the 120-entry probe that classified
    it, below package code 125's 0.2649. **The all-codes fallback the register had already
    disqualified — for crediting multi-leg package liquidity to a single-leg resting order, an
    OPTIMISTIC bound — reads NPA 1.0029pp against the 1.00pp bar, while the registered primary
    reads 0.6318pp.** The arm ruled out in advance is exactly the one that crosses. **Reported
    because it cuts the other way: the void concealed no crossing** — the fallback's halves are
    1.0760 and 0.9352, so both-halves fails there too. Arithmetic, **not a verdict**.
  * **A PASSIVE FILL IS NOT A FREE HALF-SPREAD, AND THIS IS THE QUOTABLE MEASUREMENT.** Resting at
    the mid over 30 minutes: gross saving **+2.4555pp**, adverse selection **−1.8237pp**, net
    **+0.6318pp** (CI95 [0.5014, 0.7643]), fill rate **0.5726**. **ADVERSE SELECTION EATS 74.3% OF
    THE GROSS SAVING** — a resting bid fills when sellers are aggressive, and *"you save half the
    spread"* overstates by nearly fourfold.
  * **`ρ` = 0.6743: A REAL TRADE PAYS TWO THIRDS OF THE QUOTED HALF-SPREAD** (CI95
    [0.6617, 0.6871]; 0.6054 all-codes; unweighted agrees at 0.6737). **The decomposition keeps
    apart two things that would flatter the answer if added:** EOD half-spread **$0.1544** →
    prevailing-at-print **$0.0999** → effective **$0.0591**. The **$0.0545 availability term is
    SELECTED** — you avoid it only if you trade when the market is there — and **may never be
    quoted as a saving**; only the **$0.0408** price-improvement term is an execution property. So
    of an apparent **$9.53/contract** overcharge just **$4.08** is defensible.
  * **THE STRONGEST CONDITIONING IS ENTRY PREMIUM, NOT QUOTED SPREAD** (the registered expectation
    was wrong): `ρ` falls monotonically **0.778 → 0.597** with premium, range 0.1812 against a
    permutation p95 of 0.0376 — **4.8× the null**, negative Spearman in both halves and both arms.
    A cheap option pays nearly its whole quoted half-spread; a fixed tick on a small premium is why.
    **`F6` (print size) is DEGENERATE** — two of five bins **empty**, print size being overwhelmingly
    one contract — and is flagged, not reported as a failure, per O13's treatment of `opt_right`.
  * **THE LIMITATION THAT MUST TRAVEL WITH EVERY FIGURE ABOVE: coverage is 0.7162 and the excluded
    28% is NOT random.** The tape-thin contracts carry **62% wider spreads, ~half the market cap and
    ~half the ATM open interest, and NEGATIVE expectancy (−3.11% vs +5.82%)**. **Every number here
    is measured on the LIQUID part of the book**, and cost bites hardest on the part excluded —
    O13 already found `entry_spread_pct` q5 at −7.41%.
  * **A PROCESS DEFECT, MINE: C2 and the outcome statistics were computed in the SAME pass**, so it
    cannot be claimed the control was read before the numbers. A gating control must run and be read
    in a **separate pass**. Also: the `λ=+1` row is the instrument's own null, should read 0 by
    construction and reads **−0.07 to −0.59pp** (late-session reference moments with truncated
    windows) — a measured bias that runs **against** the passive arm, so it does not manufacture the
    null. **The O14 staleness caveat was checked and does NOT bite here: median quote lag 0.0s,
    0.19% over 60s.**
  * **NOTHING IS ADOPTED. `DEFAULT_AGGRESSION` is untouched at 1.0 and pinned by test**; a material
    result is **routed to Don**, because changing the fill constant re-prices every options figure
    the project publishes. **AND CHEAPER FILLS DO NOT RESCUE R2** — the random-entry control is
    filled by the identical rule, so the **−5.0640pp** gap is untouched. That `ρ < 1` means every
    options expectancy in the record is **understated** is *not* evidence the signal works.
  * **Options `N` 248 → 258** (4 + 6, exactly as pre-committed), **charged in full despite no
    verdict** — declining to run keeps the denominator (session 8), but running and then voiding
    does not refund the search. **Equity `N` untouched at 155.** Expectations scored **8 right,
    3 wrong, 1 split, 1 unscorable**. `data/free_analysis/O10_O18_TICKFLOW.json`;
    `HANDOFF_optionsbot.md` §34-37.
- **THE PRICER'S DIVIDEND GAP IS A CALLER BUG, NOT A MODEL BUG — IT IS CHEAP WHERE IT IS
  MEASURABLE AND ONE DOOR IS UNRESOLVED; AND THE PER-BUCKET FLOOR CANNOT DELIVER WHAT ITS OWN
  COMMENT PROMISES (2026-08-11, session 25, `O21` + `O26`).** Frozen book, no re-mine, **no live
  code path changed**. `PREREG_o21_dividends.md` and `PREREG_o26_bucket_floor.md` were committed
  **together and ALONE at `bf5324c`** — two `.md`, zero `.py`.
  * **`O21`: `bs_price`, `implied_vol` and `greeks` ALREADY take a dividend yield `q` and handle
    it correctly. Every caller uses the default `0.0`.** So **anyone who "adds dividend support
    to the pricer" is fixing the wrong thing** — pinned by a test. And the banked P&L comes from
    **QUOTED bid/ask**, so the pricer cannot move it directly; it reaches the book only through
    early exercise, contract selection and stored derived fields.
  * **EXPOSURE IS WIDESPREAD, THE MEASURED COST IS NOT.** 81.4% of trades are on dividend payers
    (median trailing yield 2.02%) and **2,107 of 3,870 calls span an ex-div date** — yet only
    **34 exits (0.879%) were booked below intrinsic, worth +0.2002pp** against a pre-registered
    1.00pp bar. **Measured MODEL-FREE (`bid < S − K`)** so the answer is not a function of the
    pricer under test. Controls first: parity recovers the stored entry spot at median relative
    error 0.00232, and the simulation's **own** bars at **0.00000, 100% within 1%**.
  * **THE UNRESOLVED DOOR, REPORTED AS UNRESOLVED RATHER THAN AS ZERO.** The `q = 0` control
    reproduces the banked contract **3,870/3,870 = 100.00%**; the corrected pricer picks a
    **different contract on 179 entries (4.63%)** and **not a near-substitute** — median
    **|delta gap| 0.129** against a 0.35 target, **93.9% moving to a LOWER strike**, the predicted
    direction. **Its P&L is NOT COMPUTABLE on the frozen book:** the freeze holds full chains
    only on **ENTRY** dates, so a contract the book never held has no forward price path (median
    **2** chain dates). **Closing it needs a re-mine and is the recommended next item.**
  * **THE PRICER IS DELIBERATELY NOT CHANGED** — neither clause of the materiality bar is met,
    and passing `q` into `pick_contract` would change **which contract the live engine buys on
    4.63% of entries**: a construction change, not a bug fix. The non-change is **pinned by two
    tests**, the discipline session 16 used for sizing and session 20 for `zscore`.
    D3 for the record: `q = 0` **understates** solved IV by a median **0.00617** (~0.62 vol
    points) and **overstates** |delta| by 0.00668; `delta85` firing moves 6 → 2 of 3,870, which
    cannot disturb its −0.02pp rejection.
  * **TWO DEFECTS IN MY OWN INSTRUMENT, both caught before any verdict was read and both pinned.**
    Spot at exit was first estimated as `max(call_bid + strike)` — parity's **loosest UPPER
    bound** — which inflated the early-exercise gain to **+5.62pp, eight times the truth**, in
    the direction that manufactures a material finding; the parity replacement then rejected
    zero-value puts and so discarded exactly the deep-ITM cases early exercise lives in, scoring
    **zero rows**. **Also found: `options_backtest.BARS_CACHE` is a RELATIVE path**, so it
    silently resolves to nothing from a git worktree and returns an empty bar set rather than an
    error.
  * **`O26`: NULL — `MIN_CLOSED_PER_BUCKET` STAYS 30, AND THAT IS NOT A VINDICATION OF 30.** The
    constant's own comment — *"enough that one lucky contract cannot flip the verdict"* — is
    testable and had never been tested. `P_flip(n)`, the chance that removing the single most
    extreme trade flips a bucket's sign, **never reaches the 0.05 bar anywhere on the
    pre-committed grid**: **0.1848 at the shipped 30** and still **0.1084 at n = 300**. Going
    30 → 300, a tenfold rise **no live bucket could supply**, buys almost nothing.
  * **THE SECOND HALF IS THE STRONGER RESULT AND IT WAS CHECKED AGAINST CLOSED FORM, NOT
    TRUSTED: half-to-half sign agreement is a COIN FLIP at every bucket size** — 0.4942 at n = 30,
    0.5482 at n = 300 — and the book's own moments (mean 0.0327, sd 0.9251) **predict that curve
    analytically** (0.5059, 0.5561). **A bucket would need ~6,148 trades for its two halves to
    agree on the SIGN of expectancy 95% of the time; the whole book is 3,870 and the largest live
    bucket is 2,058, with small-cap at 44.** So **per-bucket expectancy on this book is
    essentially unmeasurable at ANY floor** — a third independent corroboration of R2 and O13.
    **Do not raise the floor; stop making per-bucket expectancy claims on this book.** Zero live
    buckets change status.
  * **Options `N` 246 → 248** — one trial each. **O21 was first charged ZERO** on the reasoning
    that a correctness measurement is a `FIXED`-class row, and **another lane's research-page
    test rejected it**: the log schema requires every non-`FIXED` row to charge at least one
    trial, and this row is not `FIXED` because nothing was repaired. It had a pre-committed bar
    and returned a verdict against it, so it is a trial — **corrected upward**, against my own
    result. **Equity `N` untouched at 155** and `BACKTEST_RESULTS.json` needs no re-run.
    Expectations scored **6 right, 4 wrong** across the two items.
    `data/free_analysis/O21_DIVIDENDS.json`, `O26_BUCKET_FLOOR.json`;
    `HANDOFF_optionsbot.md` §29-33.
- **THE OPTIONS ANTI-SIGNAL IS DIFFUSE, ENTIRELY WITHIN-BIN, AND CANNOT BE TRADED — AND THE DEAD
  ENTRY COSTS 2.75× IN POSITION SIZE (2026-08-11, session 24, `O13` + `O12`).** Two ledger items,
  one session, on the banked split-clean books; `PREREG_o13_antisignal.md` and
  `PREREG_o12_kelly_ruin.md` were committed **together and ALONE at `b0f287d`** — two `.md`, zero
  `.py`. **R2 is NOT re-opened; this characterises the corpse.**
  * **THE FINDING THAT CLOSES OFF A FAMILY OF REPAIRS: the −5.0640pp gap is ENTIRELY a WITHIN-BIN
    (rate) effect, not composition.** Across **all 32 feature arms** the rate component runs
    **−4.23pp to −5.79pp** against the −5.0640pp total, while the largest **mix** component
    anywhere is **0.7711pp — 15.2% of the gap**, most under 0.2pp. **The alert does not lose
    because it picks different CONTRACTS from random entry; it loses inside every kind of contract
    it picks.** So "trade longer-dated / tighter spreads / bigger names" are all composition fixes
    aimed at the wrong thing.
  * **Q2 DIFFUSE and Q3 (the inverse) NULL.** Nothing clears its own calibrated p95 in **both**
    halves — 4 of 32 clear full-sample against **~1.6 expected at a 5% bar over 32 correlated
    arms**. The decide-half refusal rule **makes the measure half WORSE in both directions**
    (early→`dte`/q2 −0.0977pp, late→`iv`/q3 −0.7774pp) and **the two directions select DIFFERENT
    features** — session 7's LOO pattern for the third time. `iv` q3 is the **worst** bin on the
    late half and nearly the **best** on the early half.
  * **YOU CANNOT SHORT THE GAP, and this is the most likely misreading.** The anti-signal is
    **RELATIVE to the control, not absolute** — the alert book's own expectancy is **positive**
    (+3.2702%/trade) — so mechanically reversing it is negative before any cost, with the
    round-trip spread on top. It is a reason not to pay for the alert, not a tradeable short.
  * **REPORTED BECAUSE IT LOOKS LIKE A FINDING AND IS NOT: `dte`.** Alert expectancy climbs
    monotonically with tenor (**−0.35% → +7.63%**) while the control stays flat, and q2's gap is
    **−10.84pp** — but it **fails its own calibrated bar** (0.472 vs p95 0.497) and clears in one
    half only. **Do not act on it.** This is exactly what the X7 calibration method is for.
  * **`O12`: `f*` = 0.0403 and the verdict is NOT USABLE — but the HALVES AGREED (1.758 against a
    2.0 bar); the bootstrap CI95 [0.0000, 0.1001] includes zero.** Right answer, wrong reason.
    **At full Kelly P(drawdown > 50%) is 0.753 for a median +26.7%/yr**; quarter-Kelly keeps most
    of the growth (1.114 vs 1.267) at 0.006. **At f = 0.10 — only 2.5× Kelly — the MEDIAN outcome
    is a LOSS on a positive-expectancy book.** Kelly here is conditional on a distribution R2 has
    already shown is worse than random entry, so **no fraction is a recommendation for real
    money**; live flat 1-contract sizing is **unchanged**.
  * **R2 RESTATED IN SIZING TERMS, and it is new: the random-entry control supports `f*` 0.1110,
    2.75× the alert book's.** The dead entry costs not only expectancy but the size the book can
    carry. Flat sizing ($257/trade at the median premium) equals `f*` at **$6,371** equity — so
    the live book is under-sized above that and **over-sized below it**.
  * **THREE DEFECTS, none in the live product.** `iv_rank` is **wired and 0.0% populated on BOTH
    books** (COVERAGE-RULE class). **`opt_right` and `horizon` are CONSTANT — the banked options
    book is 100% calls and 100% `swing`** — so every options claim this project makes is about
    long calls at swing horizon only, and those two arms are flagged degenerate rather than
    reported as failures. The alert **label vocabulary is PARAMETERISED** (`Low IV 14%`…`19%`,
    `Volume surge 1.5x`…`1.9x`), inflating 17 registered arms to **32**; the registered definition
    was kept and the **trial cost corrected UPWARD**, against the register's own result.
  * **17 of 100 bins DO lose money outright** — the widest-spread, least liquid ones
    (`entry_spread_pct` q5 **−7.41%**, `pit_median_spread_pct` q5 −5.53%). That **refuted a
    pre-registered expectation** and is the recommended next item: `entry_spread_pct` as its own
    registered refusal rule, which inherits O13's discouraging Q3a prior.
  * **Options `N` 210 → 246. Equity `N` UNTOUCHED at 155** and `BACKTEST_RESULTS.json` needs no
    re-run — the trial counter is domain-scoped. Expectations scored **5 right, 1 split, 2
    wrong** across the two items — the split is flat-sizing-below-`f*`, which holds for five of
    six account sizes and fails below $6,371. `data/free_analysis/O13_ANTISIGNAL.json`, `O12_KELLY_RUIN.json`;
    `HANDOFF_optionsbot.md` §24-28.
- **CLUSTERED INFERENCE IS NOW THE DEFAULT, AND THE RESULTS FILE HAS A FIELD-LEVEL SCHEMA GUARD
  THAT IMMEDIATELY FOUND TEN COMPUTED FIELDS BEING SILENTLY DROPPED — INCLUDING B17's ENTIRE
  DISCLOSURE (2026-08-11, session 22, `M2`/`M6`).** Both **infrastructure**: no hypothesis, no
  verdict. **Equity `N` is UNCHANGED at 155** and the Deflated Sharpe is bit-identical at
  0.8340367318547941; the two rows are logged to the **infra** domain at n=1 each (infra 8 → 10)
  on the V1 precedent, and infra `N` gates no published claim. `PREREG_m2_m6.md` committed
  **alone at `af88533`**, a strict ancestor, because M2 touches the statistic every
  pre-committed gate reads.
  * **SCOPING REMOVED MOST OF THE WORK AND WAS CHECKED AGAINST THE CODE, NOT THE ITEM TEXT.**
    The `M2`/`M6` in **`SECURITY_AUDIT.md` are a DIFFERENT pair, already fixed at `96fd8bf`** —
    the ledger's id-collision warning is real. Of the real items (`VALQUO_EDGE_AUDIT.md:1507`
    and `:1557`), **M2's entire trade-level half was already delivered by R3** (date-block
    bootstrap, purge/embargo, two `n_eff` estimates against a shuffled null) and **M6's
    block-level half by B22**. The options-bot lane had already published the correct remaining
    scope — *"the FIELD-level half does not exist at all, and that is the half the R9 loss
    actually came through"* — and that report was adopted rather than re-derived.
  * **"CLUSTERED BY DEFAULT" COULD NOT MEAN REDEFINING THE EXISTING KEYS, AND THE REGISTER SAID
    SO BEFORE THE CODE EXISTED.** `long_short_tstat` is **naive** and is what
    `holdout_compare_panels` reads — the gate whose **+0.25 t** margin was committed against it,
    which decided `SECTOR-NEUTRAL-B6`, `S20` and `S21`. The floors are **statistic- AND
    lag-specific** (naive 2.1437, HAC 2.2837, alpha HAC 2.2913, all at **lag 1**). Redefining in
    place would have silently re-quoted every verdict those gates ever produced — session 10
    exists because exactly that mismatch went unnoticed for two sessions. **So clustered is the
    default by being what the one shared function returns as its unqualified `t`, not by moving
    the record.** `statistics.py::mean_inference` is now THE definition; `fundamental_panel`'s
    four hand-rolled copies delegate to it, **bit-identical over 400 random series, max |Δ|
    0.000e+00**.
  * **`n_eff` NOW TRAVELS WITH `n`** (M2's third requirement, which nothing in the equity lane
    did). Long-short lag-1 autocorrelation **0.189046**, reproducing R9's +0.189, for **n_eff
    47.06 of 69**; top-decile alpha **0.081237**, n_eff **58.63**.
  * **THE THEME IC *t* — THE STATISTIC CARRYING X7's CALIBRATED 2.71 BAR — HAD NO CLUSTERED
    VARIANT COMPUTED ANYWHERE, EVER.** Nor did `per_signal_ic`. Both now ship `ic_inference`.
    **`ic_tstat` is untouched, so the 2.71 bar still applies to exactly the number it was
    calibrated on, and `ic_inference.t` is a NEW statistic with NO calibrated floor — nobody may
    compare it to 2.71.**
  * **REPORTED BECAUSE IT CUTS AGAINST THE CHANGE, and the pre-registered expectation was WRONG:
    the theme IC series are NOT materially autocorrelated.** The clustered *t* is below the naive
    one in only **5 of 9** themes, max |ρ| is **0.164**, and **four of nine are NEGATIVE** (which
    improves precision, so `n_eff` clips at 69). `quality` 3.1015 → 2.9837, `capital_discipline`
    2.7556 → 2.6342, `momentum` 1.3118 → **1.4182** (rises). Unlike the long-short spread
    (ρ +0.189, Ljung–Box p 0.036), **there is little serial correlation to correct.** The gap
    closed is real as **completeness**; the numbers barely move.
  * **M6 FOUND FIVE LIVE DROPS, TEN FIELDS, NONE PREVIOUSLY KNOWN.** `_backtest_hold` computes
    **B17's WHOLE disclosure** (`label_warning`, `target_n`, `exit_rank`, `held_min/median/max`,
    `charges_costs`, `charges_taxes`) **and `build_payload` carried none of it** — so
    `portfolio.cagr`, the number this file calls the noisiest in the results, shipped with no
    warning that the book holds ~`exit_rank` names rather than `top_n` and pays neither costs nor
    taxes. **The fix for B17 was being computed and thrown away.** The canonical file now carries
    **`held_median = 42`** for the book labelled "top 25". Separately, **session 12's
    `adopt_detail` and `challenger_weights_cols`** — banked so "what would this run have scored
    one haircut lower" is arithmetic — never reached the file a later session would read.
    **Banking a number into a dict nobody serialises is not banking it.** `SCHEMA_VERSION` 4 → 5,
    purely additive.
  * **THE TENTH FIELD IS THE BEST EVIDENCE FOR THE GUARD, because the guard found it against its
    author.** `ev_freshness.rows` — the **denominator** of the `fresh` fraction — was caught **on
    the guard's first real run**, and it had escaped the hand-built spec because that spec was
    derived by walking each producer's AST while `ev_freshness` builds its dict incrementally
    (`out["rows"] = int(n)`). **Static analysis could not see it; a runtime producer-enumerating
    guard could.** That is M3's thesis — *a guard reading a registry cannot see an unregistered
    field* — demonstrated on my own static pass.
  * **A DEFECT IN THE CHANGE ITSELF, CAUGHT BEFORE SHIPPING: THE GUARD WOULD HAVE BEEN
    SWALLOWED.** `main()` wraps the results write in `try/except Exception` commented *"Never
    allowed to fail a completed backtest"* — right intent, but it would have caught
    `PayloadSchemaError` and printed it as a warning nobody reads. **A check that cannot fail
    anything is not a check, which is the exact pattern M6 exists to close.** It now has its own
    handler **ordered ahead of** the blanket one, keeps every artifact already written, and exits
    **non-zero**; pinned by an AST test. **No environment-variable escape hatch** (`RUN_RULES`
    A5) — the allowlist is the legitimate door and it leaves a diff.
  * **THE INTEGRATION TEST FAILED FIRST, WHICH IS WHY IT IS WORTH ANYTHING.** The full-universe
    run completed every computation and then **failed at the write step** on `ev_freshness.rows`,
    writing both files first and exiting non-zero exactly as designed; the re-run after the fix
    passes with `errors: []`. **C1 holds: leaf diff 1,217 → 2,423 leaves, 1,206 added, ZERO
    removed, and all nine real moves are last-digit float noise in the cost curves.** Every
    headline is bit-identical.
  * **`archive_scan` NOW RECORDS *WHY* A ROW WAS BLANK.** It named ten keys and stored
    `fair_value` but neither the refusal flag nor its reason, so the permanent,
    survivorship-free archive could not tell *"we declined to value this"* from *"we never
    tried"*. Reported by the live-data lane as **"edge lane, not mine"** — it was this lane's.
  * **STILL OPEN, REPORTED NOT FIXED: the CPCV embargo is ONE rebalance period against a 252-day
    feature lookback** (`ret_12_1`), so a test period's realised returns feed the momentum
    features of the next **four** training dates. M2's own last paragraph. Fixing it moves PBO,
    the Deflated Sharpe and the adopt gate, so it is a **results change** needing its own
    register. Also **`valuation/engine/calibration.py:737` is a FOURTH hand-rolled naive
    t-stat** — engine lane, untouched.
- **THE STANDARDISER IS WORTH SEVERAL POINTS OF ALPHA AND NO THEME IC CAN SEE IT — S20 REJECTED,
  S21 NOT REPLICATED, AND THE STANDING RULE IS NOW PROVED RATHER THAN ANECDOTAL (2026-08-11,
  session 21, `S20`/`S21`).** Ledger items S20 ("rank composite, not z-sum") and S21 ("winsorise
  before standardising"), both `OPEN`, both `src=auto`, neither ever run. They are the same
  decision twice — how a cross-section becomes a number before the weighted sum — and P6.3 is why
  they got a register: robust z-scores **halved the long-short *t*** while every per-signal IC
  stayed flat. `PREREG_s20_s21_construction.md` was committed **alone at `27af414`**, a strict
  ancestor of the measurement commit, running **the SAME shipped `holdout_compare_panels` gate with
  the SAME already-committed margins** (+0.25 long-short *t* AND +100bps alpha, in **both** halves,
  boundary embargoed) under **two** pre-specified weightings and no others. **One panel build,
  three scorings, 113,945 identical rows.**
  * **THE HEADLINE IS THE PAIR, NOT EITHER ARM: the two arms move top-decile alpha by −3.49pp and
    +2.43pp per year, and NOT ONE THEME IC MOVES AS MUCH AS 0.4 OF A *t*** (max |Δ| **0.1920** and
    **0.3558**; `insider` moves **exactly 0.0000**, `capital_discipline` +0.0001, `size` −0.0017).
    Judged by per-signal or per-theme IC both changes look harmless. **The standing rule — never
    judge a construction change by per-signal IC — is now demonstrated three times (P6.3, X3, here)
    and, for a rank transform, is a mathematical IDENTITY rather than an observation:** control C5
    measures `max |ΔIC| = 0.000e+00` across all 44 number columns, because Spearman IC is invariant
    to a strictly monotone transform. **The composite is a weighted SUM and is scale-sensitive; the
    book is the deliverable.**
  * **S20 (RANK) IS REJECTED — AND IT FAILS WHILE MAKING THE DECILES *BETTER* ORDERED.** Deployed:
    alpha **+7.17% → +3.68%** (−3.49pp), long-short **+11.04% → +9.04%**, *t* 2.8361 → 2.3054, HAC
    **2.6199 → 2.0588**, alpha HAC **4.3762 → 2.0028** — so the rank arm **fails BOTH calibrated
    floors** (2.2837, 2.2913; **an EXTRAPOLATION** for a challenger arm) where the shipped arm
    clears both — while **monotonicity IMPROVES −0.8909 → −0.9515**. Rejected in **both halves** and
    again under flat weights. **The dissociation is the finding:** ordering *across* deciles gets
    smoother while the **top** decile, which is the product, loses its edge — D1 25.31% → 21.82%.
    Hypothesis, not a result: rank discards the magnitude information that identifies genuinely
    extreme names.
  * **S21's PREMISE IS WRONG AND THE REGISTER SAYS SO BEFORE THE RUN: `zscore` ALREADY winsorises
    at 2% before standardising**, at both layers (`cross_sectional.py:83-87`). The audit item
    proposes the shipped behaviour — which is what `src=auto`, *"a lead, not a fact"*, exists to
    warn about. So the arm actually run is **winsorisation OFF**, and an adopt would have meant
    **removing** the shipped clip.
  * **S21 IS NOT REPLICATED, AND IT IS THE MOST INTERESTING NEGATIVE IN THE FILE.** Full sample,
    every headline improves and several hugely: alpha **+7.17% → +9.60%** (+2.43pp), long-short
    **+11.04% → +16.63%**, *t* **2.8361 → 4.9395**, HAC **2.6199 → 4.3612**, monotonicity −0.9758.
    **But the gate splits: the late half passes (Δt +2.0125, Δalpha +3.69pp) and the EARLY half
    fails on the alpha margin BY 17 BASIS POINTS** (+0.83pp against the +1.00pp bar) while clearing
    the *t* margin. **Under flat weights it REJECTS outright**, both halves negative. Paired
    within-panel: +2.43pp/yr at HAC *t* **+1.9170**, long-short +5.59pp at **+1.9365** — **both
    below even the UNCALIBRATED 2.0.** Ambiguous against its own threshold is a **NULL**
    (`RUN_RULES` A6). Session 7's LOO pattern for the fourth time.
  * **THE CAUTION THAT MUST TRAVEL WITH THAT +2.43pp, or the number will be misquoted: the
    unclipped arm's most extreme composite averages 7.14× its OWN 99th percentile, against 1.64×
    for the shipped arm**, and only **8 of the shipped top 25 names** survive it. An unclipped
    z-score is a **fragile estimator** whose book is anchored by outliers. **Winsorisation is also a
    DATA-QUALITY defence, not only a statistical choice** — P7 shipped a currency bug that computed
    `book_to_price` **892 against a true 0.589**, and with no clip such a row dominates the whole
    cross-section's mean and sd. *"Removing the outlier guard improved the backtest"* and *"the
    outlier guard is not earning its keep"* are different claims and only the first is measured.
  * **A DEFECT IN THIS REGISTER'S OWN CONTROL, FOUND BY MEASUREMENT AND CORRECTED RATHER THAN
    DROPPED: C7 claimed a rank arm must be BIT-IDENTICAL under winsorisation. IT IS NOT.** Rank is
    invariant to **strictly** monotone transforms; winsorisation is only **weakly** monotone — flat
    in the clipped tails — so it creates **ties**, and a percentile rank is not invariant to ties.
    The differences sit in the clipped tails alone and the middle of the distribution is exactly
    invariant. **So S20 does NOT strictly subsume S21**, and the same mechanism gives the asymmetry
    worth keeping: **S20 is invisible to a per-signal rank IC; S21 is visible to it.** Pinned by
    test.
  * **Single-input themes are RANK-INVARIANT under a standardiser swap and multi-input themes are
    not** — `size`, `capital_discipline` and `insider` post a within-date rank correlation of
    exactly **1.0000**, because a monotone transform of ONE column preserves its ranking, while
    `quality` (ten inputs) is the most changed theme in both arms (0.9395, 0.8215). A mean of
    monotone transforms is not a monotone transform of the mean. **The pre-registered expectation
    said `size` would move most; it cannot, and the prediction was backwards.**
  * **Controls: C1 reproduces the published record to the digit; C2 113,945 identical rows across
    all three arms, 69 dates, 2,531 names; C3 both toggles far from inert (composite rank
    correlation 0.8859 and 0.7819, ~65-69% of names change decile); C4 no new missing values;
    C5 exactly zero; C6 `sentiment` empty and `insider`'s layer-1 exemption verified at max|diff|
    0.0 over 94,660 rows; C7 falsified as above.**
  * **Equity `N` 151 → 155** (two hypotheses × two weightings, no grid), √(2·ln 155) = 3.1760.
    **ADOPTS NOTHING**, and the register fixed that in advance: an eligible arm is recorded
    **ELIGIBLE, not adopted**, and **QUEUES BEHIND the theme restoration's vintage** rather than
    spending a second five-year clock reset on the same restart. Expectations scored **2 right,
    3 wrong, 1 split** — the streak continues, which is why they are written down first.
  * **THE QUEUEING CLAUSE TURNED OUT TO BIND, WHICH IS WHY IT WAS WRITTEN BEFORE THE RESULT: the
    theme-restoration lane took the vintage event THE SAME DAY** (`c8efd00`, `PREREG_theme_restoration.md`
    committed alone at `1d12822`), restoring `capital_discipline` to the live path on a fidelity
    gate while `institutional` (+0.1706) and `insider` (+0.3596) failed it. **Nothing here
    conflicts, because both arms failed their own gate** — but had either been eligible, adopting
    it separately would have spent a **second** clock reset for one restart's worth of evidence.
    The clause cost nothing to write and would have been unarguable to add afterwards.
- **SECTOR-NEUTRAL IS REJECTED AGAIN — AND IT FAILED *DIFFERENTLY*: THE TRADE-OFF THE ORIGINAL
  REJECTION RESTED ON DOES NOT EXIST ON THE CORRECTED PANEL (2026-08-11, session 20,
  `SECTOR-NEUTRAL-B6`).** Item **B** of `HANDOFF_parked_positives.md`. Sector-neutral ranking was
  rejected twice — P10 (2026-07-31) and 2026-08-02 — but **both rejections ran on the pre-B6
  110-date / 2,710-name panel the project has since declared void**, and the decision turned on a
  **−1.58pp alpha difference measured inside a panel whose alpha LEVEL moved −4.18pp when B6 was
  removed**. `PREREG_sector_neutral_b6.md` was committed **alone at `1bdb7e0`**, a strict ancestor
  of the measurement commit, re-running **the SAME shipped `holdout_compare_panels` gate with the
  SAME already-committed margins** (+0.25 long-short *t* AND +100bps alpha, in **both** halves,
  boundary embargoed) under **two** pre-specified weightings and no others.
  * **REJECTED under BOTH weightings, failing in BOTH halves.** Deployed: top-decile alpha
    **+7.17% → +6.09%** (Δ **−1.09pp**), long-short **+11.04% → +8.51%**, long-short *t*
    **2.8361 → 2.3423**, HAC **2.6199 → 2.1505**, monotonicity −0.8909 → −0.8667. Flat weights
    give the same answer, so **the verdict does not rest on a choice of weighting**.
  * **THE FINDING IS NOT "IT FAILED AGAIN", IT IS *HOW*.** On the void panel sector-neutral
    **BOUGHT long-short *t*** (3.396 → 3.896, **+0.500**) and **sold alpha**, and the rejection was
    a *judgement* that a long-only book should not make that trade. **On the corrected panel the
    gain is GONE AND ITS SIGN IS REVERSED** — **−0.494** deployed, **−0.300** flat — so
    sector-neutral is **worse on BOTH metrics and there is no trade-off left to adjudicate.**
    The rejection no longer depends on preferring alpha to a *t*-statistic.
  * **THE CALIBRATED FLOOR SEPARATES THE ARMS: the shipped arm clears the long-short HAC floor
    (2.6199 vs 2.2837) and the sector-neutral arm does NOT (2.1505).** Both clear the alpha HAC
    floor (2.2913). Quoted where X7/session 10 calibrated them — the full-universe decile book,
    69 dates, H = 63, lag 1 — and **labelled an extrapolation for the sector-neutral arm**.
  * **ONE PANEL BUILD, TWO ARMS, A PROVABLY IDENTICAL ROW SET — an improvement on both prior
    runs, which built the arms as two SEPARATE runs.** Each cross-section calls `build_frame`
    twice on the same `metrics` list, so the **`insider` nondeterminism this file records is
    common-mode and cancels** instead of landing inside the difference. Controls: identical
    `(date, ticker)` key sets (113,945 rows each); the toggle is **not inert** (composite
    correlation 0.9836, nine of ten themes move); the flat arm **reproduces the published record
    to the digit**; **sector coverage RE-MEASURED on the corrected panel at 100.0%, 11 sectors,
    smallest sector 50 names, ZERO singletons** (the 100% in the record was measured on the *void*
    panel); `insider` untouched at exactly 0.000; no new missing values; `sentiment` empty.
  * **A DEFECT FOUND AND REPORTED, DELIBERATELY NOT REPAIRED: `cross_sectional.zscore`'s
    zero-variance guard is VALUE-DEPENDENT.** It tests `sd == 0`, but whether a constant column
    has an exactly-zero pandas variance depends on the constant — exact for 0.0, 50.0, 2.5,
    0.125, ~1e-16 for **0.9, 0.1, ⅓, 12.34**. When it misses, `zscore` returns **a fabricated
    pattern with max |z| = 1.0 built from floating-point residue, not NaN** — so *a constant
    signal does not reliably neutralise itself.* **It also corrects the record: V2G's "a constant
    `insider` makes `zscore` return all-NaN" holds only because the live `insider` is constant at
    exactly 0.0 (`(50−50)/25`), and is not a general property.** **Exposure MEASURED, not
    assumed: nil** — no theme column is degenerate on any of the 69 dates, and the smallest
    within-sector dispersion over 231 sampled cells is 0.2209. **Not repaired because `zscore` is
    on the live scoring path, so changing it is a scoring change and therefore a VINTAGE EVENT**;
    pinned by a test that fails if it is ever silently corrected.
  * **CLOSED PERMANENTLY, by a clause fixed before the run: full sector-neutral ranking may NOT
    be re-run as a re-run.** Re-opening requires **new data** (`S25`, a genuine point-in-time
    sector map — TICKERS is today's classification and is the one non-point-in-time input in the
    panel) or **a materially different construction** (`S15`, sector-relative on the **value
    theme alone**, never tested at all). Both ledger rows are now scoped rather than blank.
    **Nothing here touches the sector column's ACCEPTED use for the `max_sector_w` concentration
    cap — a risk control, not a re-ranking.**
  * **Equity `N` 149 → 151** (one hypothesis, two weightings, no grid), √(2·ln 151) = 3.1677.
    **ADOPTS NOTHING and `CONFIG.sector_neutral` is untouched at `false`.** Four of five
    pre-registered expectations were RIGHT and one split — unusual here, and the stated reasoning
    held: the corrected window is roughly the void panel's late portion, where sector-neutral
    already lost on both metrics.
- **THE EXIT RULE WAS RACED AND NOTHING BEATS THE INCUMBENT — BUT NEVER SELLING COSTS
  10.89pp/yr, AND THAT CONFIRMS S22 RATHER THAN CONTRADICTING IT
  (2026-08-11, session 19, `S23`).** The live book holds a name until it falls out of the top 50,
  min-hold 2, and that exit had never been tested against an alternative. One buy rule and an
  identical `min_hold` across every arm, so only the exit differs.
  `PREREG_s23_exit_rule.md` was committed **alone at `6a73485`**, a strict ancestor of the
  measurement commit, with **both TP/SL pairs named from published convention and NO grid swept** —
  `sweep_hold_params` already sweeps `trailing_stop` over four values and picking its best cell is
  the in-search +8.43%/yr → locked hold-out −0.04%/yr failure already paid for.
  * **NO CHALLENGER BEATS THE INCUMBENT.** Fair-value point -0.13pp/yr
    (HAC *t* -0.368), fair-value lens band
    +0.37pp (+0.866),
    O'Neil +25/−8 -0.21pp (-0.396),
    2:1 +20/−10 -0.13pp (-0.254) —
    **all under 0.4pp/yr in either direction on 69 paired periods, net of costs**; per-arm placebo floors A1_FV_POINT 1.9181, A2_FV_LENSBAND 1.8518, A3_TPSL_ONEIL 2.0260, A4_TPSL_2TO1 2.0489, C_NEVER 2.5543.
    **THREE OF THE FOUR FLIP SIGN BETWEEN HALVES**, and the only arm with a positive full-sample
    difference is exactly the one that fails the both-halves requirement. Session 7's LOO pattern
    again.
  * **THE CONTROL IS THE ONE MEASURABLE EFFECT AND IT IS LARGE: never selling costs
    10.89pp/yr at HAC *t* -3.801**, the book grows to
    **417 names** and alpha vs the equal-weighted universe collapses
    **15.48% → 3.37%**.
    **THIS DOES NOT CONTRADICT S22, AND READING IT THAT WAY IS THE MAIN WAY IT GETS MISUSED.**
    S22 measured a cohort selected on ONE date beating the universe for ~8 quarters; a never-sell
    book keeps **buying**, so it accumulates cohorts of every age and over 69 rebalances converges
    on a 417-name slice of the universe. **Dilution, not friction** —
    its gross 20.61% barely differs from its net because it never
    trades. *"The edge persists" and "hold forever" are different claims, and only the first is
    true.*
  * **THE LEVELS ARE NOT A NEW HEADLINE.** `_backtest_hold` is the concentrated top-25→50 book
    **B17** already calls the noisiest number in the results file. S23 quotes **differences
    between exit rules** on that object; the incumbent's own CAGR is not a claim it makes.
  * **THREE DEFECTS FOUND AND FIXED, all reported in their own right.** (a) **`build_valuation_panel`
    still carried the B6 per-ticker tail** — measured on the same 25 names it gave **110 rebalance
    dates from 1998-12-31** (the inverted-universe window) against the corrected **69 from
    2009-01-15**; **any prior `run_calibration` conclusion should be re-run before it is quoted.**
    (b) **The point-in-time valuation was fetching LIVE Yahoo prices** through `_resolve_beta`'s
    corroboration rung — valuing 1999 with a beta regressed on 2021-2026 returns — **157 calls per
    1,122 rows**; there is now an explicit offline mode and the build **asserts zero network
    calls**. (c) **`_backtest_hold` extracted a column once per NAME instead of once per date**,
    114,774 extractions per call, each deep-copying the panel's `.attrs`: **61 of 70 seconds**,
    fixed 15.6s → 2.7s and **proved bit-identical over 1,818 leaves**.
  * **Equity `N` 143 → 149.** **ADOPTS NOTHING** — adoption is a **VINTAGE EVENT** that resets the
    five-year clock for zero statistical gain, and is Don's call on this evidence. Whether the
    stop-loss or the take-profit does the damage is recorded **UNRESOLVED**, because the two
    arms differ in both legs at once and adding a one-legged arm now is the grid search the
    register forbids.
- **THE EDGE DOES NOT DECAY OVER TWO YEARS, THE LONG-SHORT SPREAD DOES, AND A HOT NAME LASTS
  ONE REBALANCE (2026-08-10, session 18, `S22`).** Every HEADLINE figure the project publishes is
  measured at a single 63-day forward window because `build_fundamental_panel` computes one
  `fwd_ret` and the deployed rebalance equals it — an inherited default, never a measured optimum.
  **CORRECTION TO S22's OWN REGISTER, recorded because the register is left unedited: it claimed
  "nobody has ever asked what the composite predicts at 6 months, a year, or two years", and that
  is FALSE.** `BACKTEST_RESULTS.json` has always carried a `per_horizon` block at 63/252/756 —
  but it reports **IC and weight vectors only** (no alpha, no long-short, no decile structure), and
  `run_backtests` sets `rb = max(rebalance_days, H)` so the **rebalance period moves with the
  horizon**: 69 dates at 63d, **18** at 252d, **6** at 756d, on universes of 2,531 / 2,492 / 2,206
  names. That is exactly the confound S22 was designed to remove, and six dates support no
  inference. **It does CORROBORATE the finding, which is why it is reported: that block's
  out-of-sample IC rises monotonically with horizon, 0.038990 → 0.058241 → 0.097671 — the project
  has been shipping evidence its signal predicts better at long horizons, in its own results file,
  unread.** Direction only; the IC definitions and date sets differ. Eight horizons (1–8
  quarters) were scored from **ONE** panel build, because the grid end is `len(cal) − horizon` and a
  build per horizon would vary the horizon **and** the date set **and** the cross-sections together.
  `PREREG_s22_term_structure.md` was committed **alone at `6b187dd`**, a strict git ancestor of the
  measurement commit.
  * **VERDICT CONSTANT-RATE, by the rule fixed in advance: `R(8) = 6.195` against a ≥6.0 bar.
    Annualized top-decile alpha is ESSENTIALLY FLAT from three months to two years — +6.59%,
    +6.67%, +6.03%, +6.14%, +6.23%, +5.74%, +5.07%, +5.10%** — and cumulative alpha reaches
    **+10.20%** at eight quarters. **The alpha HAC *t* never drops below 3.16** at the
    overlap-corrected lag (7 at two years), so this is not a signal surviving on widened error bars.
    Median rank IC **rises** with horizon (+0.034 → ~+0.072), an independent route to the same
    finding that never touches the decile machinery.
  * **THE SECOND HALF OF THE HEADLINE IS THE ONE THAT CONSTRAINS QUOTING: THE LONG-SHORT SPREAD
    DECAYS AND ITS SIGNIFICANCE COLLAPSES — HAC *t* 2.7167 → 0.6846**, cumulative spread peaking at
    Q5 (+7.11%) then falling. **The persistence lives entirely in the LONG leg.** That is fortunate
    rather than damaging — the shipped product is a **long-only hot list**, so the leg that persists
    is the one users receive — but **the long-short research statistic and the product statistic
    DIVERGE with horizon, and the record has been quoting them side by side.** Nobody may quote a
    long-short figure beyond about a year.
  * **REPORTED BECAUSE IT CUTS AGAINST THE VERDICT: the classification clears its bar NARROWLY
    (6.195 vs 6.0) and DOES NOT REPLICATE ACROSS HALVES** — early **8.559** (super-linear), late
    **5.470** (would read INTERMEDIATE). Both halves agree in **sign** and both still show alpha
    accruing at two years, so **the PERSISTENCE replicates and the LABEL does not.** `R(8)` is a
    ratio whose denominator is one noisy quarter; the flat annualized-alpha column is the robust
    reading of the same data.
  * **TENURE: the top decile turns over almost completely every quarter.** 7,286 spells over 1,895
    names at a median decile size of 156. **Kaplan–Meier median spell = ONE rebalance (~3 months)**,
    naive median agrees at 1.0, **70.6% of spells last exactly one**, max 19. **One-period retention
    36.6%, INSIDE the 20–50% band pre-committed from the shipped 261%/yr turnover** — so the tenure
    measurement and the cost model describe the same book and the registered BUG branch did not
    fire. **Re-entry is the norm:** persistence-with-gaps plateaus at ~19–24% out to eight
    rebalances instead of decaying to zero, and **74% of names have more than one spell.**
    **Small caps stay LONGEST** (mean 1.788 vs large 1.224), the opposite of the pre-registration.
  * **THE DEFENSIBLE PRODUCT SENTENCE, and it must travel with its caveats:** *"the top decile beat
    the equal-weighted universe by about 6.6% annualized over the next three months and was still
    ahead by about 5.1% annualized two years later, even though a given name typically stays in the
    top decile for only one quarterly rebalance"* — **long-only, gross of costs, on the same single
    in-sample panel every other published figure comes from, not a forward test.** Display is the
    **web lane's**.
  * **WHAT IT DOES NOT SAY, and this is the most likely misuse: it is NOT a finding that the book
    should rebalance less often.** `cum_alpha(H)` is the buy-and-hold return of the cohort selected
    on ONE date; a quarterly book **re-selects and compounds fresh selections**. Those are different
    claims and only the first is measured. It does make the second **worth testing** — the book pays
    261%/yr turnover to harvest an edge still accruing at two years — but **that is S23's, needs its
    own register, and adopting it is a VINTAGE EVENT that resets the five-year clock for zero
    statistical gain.**
  * **X7's floors were NOT quoted outside the one configuration they were calibrated in** (h63, 69
    dates, lag 1) — `n`, the overlap and the HAC lag all change with the horizon, and comparing
    across configurations is the error the record already paid for twice.
  * **A per-horizon placebo was built because X7's floors do not transfer** (200 draws, fixed weights, no CPCV — a DIFFERENT and less conservative null, labelled `fixed_weights_null`, whose percentiles may never be compared with 2.2837): **8 of 8 horizons clear their own alpha floor, 4 of 8 clear their own long-short floor.** Free by-product, no verdict: the same null at h63 **without** CPCV gives a long-short p95 of **1.7494** against session 10's **2.2837** **with** selection in the loop, so **putting selection in the loop raises the 95th-percentile floor by +0.5343 of a *t*.** **Do not conflate that with the figure already in this file:** it is the shift in the **p95 over all draws**, NOT X7's post-hoc **~+1.4 mean long-short *t* among the 27% of noise draws that actually adopted**. Same direction, different quantities — a large effect on a fifth of the draws moves a 95th percentile by far less than the effect itself.
  * **CONTROLS ALL EXACT: C0 `max|fwd_ret − fwd_ret_h63| = 0.000e+00` over all 113,945 rows**; C1
    reproduces the record to the digit on a **fresh** build (alpha 0.071741, LS naive 2.836064, HAC
    2.619912, alpha HAC 4.376230, monotonicity −0.890909, EW +0.181371), so the known `insider`
    nondeterminism did not bite; **C2 dates observable 69, 68, 67, 66, 65, 64, 63, 62 — exactly one
    rebalance date lost per extra quarter**, censoring removing a **suffix**, never a scatter.
    **The defect named in advance and avoided: right-censoring is NOT delisting** — a last-price
    fallback on a censored window would return a shorter realized return labelled as a long-horizon
    one, for the most recent dates specifically. Pinned from both sides.
  * **Equity `N` 135 → 143** (eight arms; tenure, the placebo and the half-splits charged at zero). **Deflated Sharpe 0.8504 → 0.8436955925493782, √(2·ln 143) = 3.1505**, and `BACKTEST_RESULTS.json` was re-run from a clean tree so the artifact matches the record (16 of 1,217 leaves moved — five the DSR chain, four provenance, seven last-digit float; every headline bit-identical, `errors` empty, `cpcv.adopt` still false).
    **THE EXPECTATIONS WERE WRONG ON BOTH HEADLINE QUESTIONS** — SATURATING predicted at 60/40 and
    the answer is CONSTANT-RATE; large-cap tenure predicted longer at 55/45 and small is longest;
    all eight incremental quarters positive against a prediction they would not be beyond k=4.
- **THE LIVE PRODUCT SCORES A FOUR-THEME BOOK, AND WHAT THAT COSTS IS NOW MEASURED: −1.31pp/yr,
  NOT SEPARABLE FROM ZERO — BUT THE LIVE BOOK FAILS THE CALIBRATED LONG-SHORT FLOOR
  (2026-08-10, session 17, `V2G`).** The greeks lane measured over 500 served rows that three of
  the seven weighted themes reach **no live score** — `insider` is **constant** (500/500 non-null,
  one distinct value, so `zscore` returns all-NaN), `capital_discipline` and `institutional` are
  **absent** (0/500). That is **0.375 of 0.875 = 42.9% of the weight mass**, so the hot list is a
  **four-theme book** (`value`, `quality`, `momentum`, `size`) wearing the weights of a
  seven-theme one. That lane declined to price it; this register did.
  `PREREG_v2g_live_theme_cost.md` was committed **alone at `6d8750a`** before the measurement code
  existed.
  * **VERDICT IMMATERIAL, BY THE RULE FIXED IN ADVANCE: top-decile alpha +7.17% → +5.86%,
    Δ −1.3133pp against a −1.95pp bar, paired HAC t −1.4040 over 69 paired dates.** *(**CORRECTED
    2026-08-14, `MA19`: the calibrated margin at `N` = 224 is **1.8629pp**. V2G's bar was correct
    when it ran; re-read against 1.8629pp the verdict is **UNCHANGED — still IMMATERIAL**, since
    1.3133pp remains below it. The power caveat below tightens slightly and its substance stands.)*
    Building live
    sources for the dead themes is **a nice-to-have, not the project's highest-value work**.
  * **THE POWER CAVEAT IS PART OF THE VERDICT, NOT A FOOTNOTE.** The HAC se of the paired annual
    difference is 0.9354pp, so the design resolves **1.8708pp** at |t| = 2 — well matched to its
    own bar, which is what makes the null worth anything — but power against a **true** 1.95pp gap
    is **55.0%**. *IMMATERIAL means the cost could not be separated from zero at roughly a coin
    flip's power. It does NOT mean the cost was shown to be small.*
  * **THE SECOND FINDING IS THE MORE SERIOUS ONE, and the register asked for it separately: the
    live four-theme book does NOT clear the calibrated long-short floor** — HAC t **1.8811** vs
    **2.2837** (naive 2.0044 vs 2.1437), where the deployed book clears at 2.6199. It **does**
    clear the top-decile alpha floor (**3.2087** vs 2.2913), and since the shipped product is a
    **long-only hot list** that is the product-relevant statistic. So the long-only book users
    receive stays demonstrable; the long-short figure quoted beside it does not.
  * **AN IMMATERIAL ALPHA COST IS NOT A FINDING THAT THE LIVE ABSENCE IS ACCEPTABLE.** The live
    product computes a **different composite** from the one every published figure is measured
    on — the same class of defect **B7** exists to prevent. Either build the sources or quote the
    headline for the book actually computed. **Owner: screener lane**, not the edge lane.
  * **THE RESTRICTED ARM IS THE LIVE BOOK, PROVED NOT ASSUMED: `max|dev| = 0.000e+00` over all
    113,945 rows**, for both the absent case and the constant-`insider` case, because `composite`
    renormalises by the **present-weight mass**. Harness control: the incumbent arm reproduces the
    record to the digit — alpha 0.071741423321, LS naive t 2.8361, HAC t 2.6199, alpha HAC t
    4.3762, monotonicity −0.891, equal-weight benchmark +18.137%.
  * **Both halves agree in sign and neither is significant** (early −1.14pp, late −1.48pp) — a
    better stability profile than session 7's LOO arms. **Reported because it cuts against the
    verdict:** the late-half **long-short** difference is −5.63pp/yr at HAC t **−2.0639**, which
    crosses the conventional bar; not the pre-registered primary statistic, uncalibrated, one of
    six cells.
  * **EXPLORATORY, NO VERDICT** (session 7's rule: a full-sample ablation arm is not a finding):
    dropping `institutional` is the **only** one negative in both halves (−1.41% full), so **13F is
    the source to build first**; dropping `capital_discipline` is **positive in both halves**
    (+1.37%) despite holding the second-strongest panel IC (+2.76) — **X3's lesson restated, theme
    IC does not predict marginal contribution**; dropping `insider` flips sign between halves.
  * **NO CALIBRATED FLOOR EXISTS FOR A PAIRED WITHIN-PANEL DIFFERENCE** — X7 and session 10
    calibrate *levels*. The 2.0 used here is conventional and is labelled uncalibrated everywhere
    it appears. `quantile_backtest(..., return_series=True)` now returns the per-period draws
    (opt-in; default payloads bit-identical) so future paired tests use the **shipped** arithmetic.
    **Equity `N` 131 → 135, Deflated Sharpe 0.8539 → 0.8504, √(2·ln 135) = 3.1322.**
- **THE "8% CAP VIOLATION" NEVER EXISTED — `PT-SPLIT` IS CLOSED, AND THE DIAGNOSIS THIS FILE
  CARRIED FOR TWO SESSIONS WAS WRONG (2026-08-10, session 16).** The bullets below say the
  sandbox engine holds *"10 names, equal-weighted at 10% each — which the contract's own 8% cap
  forbids"*. **It forbids no such thing.** `valquo_index.build_index` sets
  `cap = max(MAX_WEIGHT, 1/len(picks))` with a comment saying why — **ten names at 8% sum to
  80%**, so on a small book the cap must relax to equal weight or the redistribution loop never
  terminates — and the payload has always self-reported `effective_max_weight`. **The weights
  were correct for the book they described.**
  * **THE REAL DIVERGENCE IS BOOK SIZE, AND IT IS ONE CONSTRUCTION FED TWO INPUTS.**
    `n = max(MIN_NAMES, round(len(large) × TOP_DECILE))` with `MIN_NAMES = 10`, so a 10-name book
    means the eligible large-cap tier held **fewer than 100 names**; the published 86 implies a
    tier of ~860. **`/admin/run-paper-track` reads `data/valquo_index.json` when it exists and
    SILENTLY REBUILDS FROM THE STORE'S LATEST SCAN when it does not** — and that scan is a top-N
    hot list. The engine was never pointed at a different strategy; it was handed a truncated one
    with no label. That is how `PT-OUTBOUND` shipped an engine figure as an Index claim.
  * **WHY THE WRONG FRAMING WAS EXPENSIVE, not merely untidy: the fix it implies is "lower a
    cap", and the cap was already right.** The actual defect would have survived the repair.
    Same lesson as the stale-figure and wrong-file-name corrections elsewhere in this file —
    **re-derive a diagnosis from the code before acting on a repeated one.**
  * **RESOLVED BOTH WAYS AT ONCE, per Don's "no third state":** `paper_track.seed_book` now
    **refuses** to seed a book that is not the Index (**≥ `CONTRACT_MIN_POSITIONS` = 50 names AND
    the 8% cap actually binding**), loudly and non-destructively — it never liquidates, because
    doing so on a conformance rule would be worse than the split. `experiment=True` is the only
    other door and it **stamps every holding row** (on the row, not in a return value: the old
    code *did* label its fallback and no surface rendered the label). The **four recorded days
    are registered in `PAPER_TRACK_CONTRACT.md` §5b** as a separate experiment, **kept not
    deleted** — its *fills* are real evidence about execution, its *return series* is evidence
    about nothing the contract binds.
  * **STILL OPEN, and it is the app lane's:** this stops the engine *adding* to a wrong book; it
    does not make it start recording the right one. That needs a conforming
    `data/valquo_index.json` on the Render disk when the cycle runs. **No vintage opened or
    closed** — the engine's series was never the bound series.
- **THE FORWARD OPTIONS BOOK WAS RUNNING EXIT LEVELS NO BACKTEST DESCRIBES, AND HELD A NAME THE
  ALERT ITSELF REFUSED (2026-08-10, session 16, `PT-BUG12`).** Both routed in by the options-bot
  lane off the first three REAL fills, both fixed in `paper_track.py`, all expected values
  pre-committed in `PREREG_session16_paper_track_repair.md` before any code changed.
  * **`_place_entry` anchors target/stop to the SUBMIT price and `mark_open` overwrote
    `entry_premium` with the FILL without recomputing either.** Systematic, not occasional:
    `auto-scan.yml` runs the cycle after the close, so the limit comes from a post-close quote and
    the day order fills at the next open. **2 of 3 open positions were off spec** (TGT +150.7%
    target against +100%; MET −46.7% stop against −50%). Levels now derive from the fill on the
    **alert's own** policy, and an idempotent repair pass fixes already-open rows every cycle.
    **All five pre-committed criteria held exactly** — TGT 8.90 → 7.1000 / 2.225 → 1.7750, MET
    9.80 → 9.2000 / 2.450 → 2.3000, **ETN bit-identical** because its fill equalled its limit.
  * **THE REPAIR RUNS IN THE FLATTERING DIRECTION AND THAT MUST TRAVEL WITH IT.** The bug made
    targets harder and stops tighter; correcting it makes them easier and looser. Right fix
    either way — the levels were wrong against the specification — but **"we fixed a bug and the
    book improved" is the easiest way for a forward test to flatter itself.** Concretely: **MET
    sat 10.2% above a stop level no backtest ever specified**, days from recording a stop-out the
    strategy under test would not have taken.
  * **A REPAIR MAY NOT EXECUTE A TRADE.** If a corrected level is already crossed, the write is
    **deferred and reported**, never auto-exited. Untaken today (no row crosses), pinned by test.
  * **`_eligible` never read `features.sizing`**, so ETN was bought on `skip: true` / *"one
    contract costs $1,610, above the $1,000 budget"* and became the **largest position in the
    book**. The veto is now honoured; **the sizing QUANTITY deliberately is not** (that would
    change construction), pinned as a non-change. **The open ETN position is NOT unwound** —
    that gate applies to new entries, and closing a live position to tidy the record is a trade
    decision.
  * **A THIRD DEFECT, same family, found while fixing the first:** the resume branch called
    `_exit_policy` on a `paper_option_orders` row, and **that table has no `features` column**, so
    the policy silently collapsed to the DEFAULTS. **Audit B5c's own comment claims that branch
    "rebuilds … the exit policy the same way the fresh path does" — the fresh path reads the
    ALERT.** It has never fired only because all three live alerts use the default policy. **A
    defect neutralised by a coincidence in the data is not handled**, so it is pinned with a
    policy that differs.
  * `options_summary.level_conformance` now reports off-spec live rows **read-only on every
    request** — it stays after the fix precisely because the first time this book was inspected,
    2 of 3 positions were off spec and nothing anywhere said so.
- **V1 SHADOW VINTAGES IS REGISTERED, BLIND, WITH NO MEASUREMENT — AND ITS POWER TABLE IS THE
  FINDING (2026-08-10, session 16).** Rule 6 (below) says an adopted change resets the whole
  five-year clock and buys nothing statistically — which, alone, means **the model can never be
  improved again without paying five years.** V1 is the escape: the closing vintage keeps being
  scored in shadow on the same dates and the two books are compared **PAIRED**, so the market
  risk that dominates a vs-SPY test **cancels**.
  * **THE GAIN IS REAL AND THE LIMIT IS STRUCTURAL, both computed before any pair exists.** At a
    between-book tracking error of 2.0 pp/yr the 60-month detectable difference is **3.34 pp/yr
    against the vs-SPY meter's 19.01** — four-fold. **But σ is small exactly when the adoption
    changed little, and an adoption big enough to matter raises σ.** No design escapes that. **A
    shadow pair that has not crossed is the EXPECTED outcome and is NOT evidence the adoption was
    worthless** — `verdict()` carries that sentence in its own output.
  * **THE CONTROL IS EXACT:** fed the contract meter's own 11.40 pp/yr TE it reproduces
    **σ 3.9847** and **~19 pp/yr at 60 months** to the digit, because it **imports**
    `track_meter.boundary` rather than re-implementing it. ρ and α are imported too and a test
    fails if they are ever copied — one boundary function in the project.
  * **BLINDER THAN ANY PREVIOUS REGISTER HERE: no vintage pair exists.** Vintage 2 opened
    2026-08-10 with no successor, so no parameter could have been tuned to a comparison even in
    principle. Vintage 2's parameters are **pinned now, in a tracked file** (`params_id
    0060c5ef3dda`), so the shadow runs a **snapshot, never a reconstruction**.
  * **No sign branch** (AST-pinned; flipping a whole series flips the verdict and moves nothing
    else), so **HARMED is exactly as reachable as CONFIRMED-LIVE**. **Research-only and fenced off
    every public surface by a test, BEFORE it has numbers to leak** — `PT-OUTBOUND` is why that
    fence is built in advance. **It does not weaken Rule 6:** it measures the price of an
    adoption, it does not refund it.
  * `valuation/edge/shadow_vintage.py`, `PREREG_v1_shadow_vintages.md`, 26 tests.
    **Equity `N` stays 131** (infra `n = 1`); the first shadow PAIR is charged when it opens.
- **AMENDMENT 1: RUN #1 IS VOID, RUN #2 IS THE LIVE TEST, AND THE PROJECT NOW HAS A VINTAGE
  RULE (2026-08-09, session 15).** Don voided run #1 (inception 2026-07-30, ~6 days, 2 rows)
  because it measured a model that has since materially changed — growth-input fix, score fix,
  universe rebuild. **Run #2: inception 2026-08-10, gate 2027-02-10, verdict 2031-08-10, with
  ZERO accrued days.** Recorded openly in `PAPER_TRACK_CONTRACT.md` **§5a**, never as a silent
  edit, and nothing above §5a was deleted.
  * **THE VINTAGE RULE.** Any **ADOPTED** change to scoring, weights or construction closes the
    current vintage and opens the next ("adopted" = ships in the live scoring path).
    **Rebalancing under unchanged rules is NOT a vintage event.** Each vintage carries its own
    clock; **the gate and the meter attach to the CURRENT vintage**, so a verdict is a statement
    *about a vintage* and must name it. The cross-vintage chain is kept and published as **"the
    system as operated"** — the honest answer to what a user would have experienced — and is
    **explicitly not the object of a verdict**, because it mixes models.
  * **RULE 6 IS THE BRAKE, AND IT IS THE PART TO REMEMBER BEFORE SHIPPING A SCORING CHANGE: a
    vintage change resets the whole accrued clock and buys nothing statistically.** §2's
    arithmetic is unchanged — 60 months at 49% power. A vintage that closes at month 30 has
    spent 30 months for no evidence.
  * **THE AMENDMENT MOVED THE CLOCK, NOT THE STATISTICS.** σ 3.9847, ρ 3, α 0.05, the cost drag
    and the SUPPORTED/UNSUPPORTED bars are **all unchanged**, so §3's *whole-run* void clause
    (which triggers on a threshold change) is not engaged; only the window-void clause is.
    Pinned by `test_the_amendment_moved_the_clock_and_not_the_statistics`. **σ was re-checked
    against the changed model rather than assumed to survive it: the current backtest still gives
    SPY excess +9.99%/yr at implied TE 11.401 pp/yr and IR 0.8759/yr** — the figures σ came from.
  * **THE DISCLOSURE THAT MUST TRAVEL WITH IT: the voided window was KNOWN to be −2.85pp.**
    Discarding a stretch that went against the strategy is the flattering direction. Three
    answers, each checkable: the cause (a model change) is independent of the outcome and its
    clause pre-existed the run; **run #2 accrues ZERO days**, so no window's sign could inform
    the new start date; and the voided rows are **kept**, visible in `as_operated()`. §5a
    forbids the thing this must never become — voiding a vintage for a change *chosen* after
    seeing the vintage go badly.
  * **Equity `N` 130 → 131** (`PT-AMEND1`), **Deflated Sharpe 0.8547 → 0.8539,
    √(2·ln 131) = 3.1226**, and `BACKTEST_RESULTS.json` was re-run from a clean tree so the
    artifact matches (14 leaves moved, five the DSR chain, four provenance, five 0.000% float;
    every headline bit-identical). Charged because void-and-restart is a degree of freedom: each
    vintage is another chance at the same hypothesis.
  * **THE METER NOW HAS A CALLER (session 15's own item).** `track_meter.detail()` ships as
    `summary()["contract_track"]` on **`/api/track`** — before this it was a tested library
    nothing called. It names **every missing trading day** on every request, is **not vacuously
    green** before the vintage starts (`recording_ok: None`, not `true`), is labelled a different
    object from the sandbox engine, and is **reconciled against `index_track.vs_spy_claim()`**,
    the one authority for a vs-SPY claim (measured −2.8468 vs −2.8468).
  * **`PT-WRITER` IS REPORTED CLOSED AND I COULD NOT VERIFY IT — the gate stays `pending`.** The
    writer is described as Cowork task `valquo-daily-track-write`, weekdays 20:01. **No such task
    is in this machine's Task Scheduler** (413 enumerate; three Valquo tasks, none this one) and
    the name is nowhere in the repo — but **no run was due yet either**, so that is evidence, not
    proof. **THE TEST IS MECHANICAL: inception 2026-08-10 is day 0, the first row due is
    2026-08-11, so from 2026-08-12 `/api/track` answers it.** Read that block before doing
    anything else with the track.
- **THE PAPER-TRACK CONTRACT IS SIGNED AND IN FORCE — OPTION E, 2026-08-09 (session 14). THE
  PROJECT NOW HAS A PRE-REGISTERED FORWARD TEST, AND TWO RECORDERS THAT DISAGREE ABOUT WHAT IT
  IS RECORDING.** Don signed: keep inception **2026-07-30** including the accrued negative days,
  **6-month operational gate (2027-01-30)**, **60-month verdict vs SPY (2031-07-30)**, the
  ~36-month costed equal-weight-basket secondary *if it is ever built*, plus a pre-registered
  anytime-valid evidence meter first rendered at the gate and monthly thereafter, whatever it
  says. `PAPER_TRACK_CONTRACT.md` §5 is the register; §6 freezes the meter.
  * **THE REGISTER BINDS THE PUBLISHED VALQUO INDEX, NOT THE SANDBOX ENGINE — because they are
    recording DIFFERENT BOOKS.** This is the session's material finding. The Index
    (`data/valquo_track.json` + `valquo_track_history.csv`, read by `index_track.py`) is **86
    names, score-weighted, max weight 2.3%, inception 2026-07-30**. The Tradier sandbox engine
    (`paper_index_track` → `data_export/paper_track_*`) is **10 names, equal-weighted at 10%
    each — which the contract's own 8% cap forbids — inception 2026-08-03.** They are not one
    track recorded twice. **Never quote an engine figure as evidence under the contract**, and
    a B7-class split stands until the engine is re-pointed or its outputs are labelled a
    different object everywhere they surface.
  * **~~The engine has never been fed (0 rows)~~ — CORRECTED 2026-08-09 (session 14): THAT WAS
    MEASURED ON THE LOCAL DEV DATABASE.** On the live Render service the engine holds **4 index
    days, 10 holdings and 3 paper option orders**, and the weekly `track-backup` Action has been
    committing them to `data_export/` all along. The rest of this bullet's session-13 findings
    stand; this one did not.
  * **THE REAL BLOCKER IS THAT NOTHING IN THIS REPOSITORY WRITES THE BOUND SERIES.** Not a
    scheduler fault, not a crash, not a conditional write — **there is no writer.**
    `index_track.py` only ever *reads* `valquo_track_history.csv`; the rows are produced by hand
    on the Cowork side, which is exactly why **four of six due rows are missing (33.3%
    coverage)**. **The operational gate cannot pass until an automated daily write exists**, and
    that is the Cowork lane's. `valuation/edge/track_meter.py:gap_report` now names every
    missing day so the failure is dated rather than discovered at the gate.
  * **THE METER IS HONEST AND WEAK, AND THE SECOND HALF MUST TRAVEL WITH THE FIRST.** A Robbins
    normal-mixture anytime-valid confidence sequence, σ **3.9847 pp/month** (the backtest's own
    11.40pp/yr tracking error inflated by R9's AR(1) design effect **1.4661**), **ρ = 3**,
    **α = 0.05 two-sided**, cost drag **0.14529 pp/month**. Measured over 40k AR(1) paths:
    false-crossing **1.5%** against a nominal 5%, but **power at the backtested +9.99%/yr edge is
    just 13.3% by 60 months and 30.7% by 120**, needing **~19 pp/yr to cross at 60 months**.
    **A meter that has not crossed is the EXPECTED outcome and is NOT evidence against the
    strategy.** The AR(1) inflation is load-bearing, not decoration: without it the false-crossing
    rate is **6.7%**, i.e. the naive version breaks its own guarantee. **σ may never be revised
    downward** — at 1.5× the assumed volatility the false-crossing rate is **20%**.
  * **GENUINELY BLIND, which is the whole point:** at the signing commit the bound series held
    **two daily rows and ZERO complete calendar months**, so no meter parameter could have been
    tuned to the outcome even in principle. Pinned by `tests/test_track_meter.py` (20 tests,
    every constant a literal), including one that fails if the AR(1) inflation is removed and one
    that pins the render decision as invariant to flipping the sign of the entire series.
  * **THE DATED AUTO-FLIP IS CLOSED, BY THE ENGINE LANE, THE SAME DAY (`126c137`).**
    `MIN_LIVE_DAYS = 60` no longer promotes the track on its own. `index_track.gate_state()`
    parses the **`Operational gate passed` row of `PAPER_TRACK_CONTRACT.md` §5** on every
    request, and `headline` requires **both** the day count **and** that row — so at any day
    count, indefinitely, the headline stays `"backtested"` until the contract says otherwise.
    **Every unrecognised outcome is not-passed** (missing file, missing row, malformed table,
    two rows disagreeing), so the failure direction is "still backtested", never "now live".
    Session 14 filled the row as `pending` and verified the parser returns `passed: false`.
    **On gate day, set that ONE row and nothing else anywhere:**
    `| Operational gate passed | YES - 2027-01-30 |`.
  * **Equity `N` 129 → 130** (the register is charged as a trial; understating `N` overstates
    significance). **Deflated Sharpe 0.8556 → 0.8547, √(2·ln 130) = 3.1201**, and
    `BACKTEST_RESULTS.json` was re-run so the artifact matches the record rather than going
    stale on the denominator again.
- **THE FORWARD PAPER TRACK CANNOT DELIVER A VERDICT FOR ~5 YEARS (2026-08-08, session 13).
  Roadmap #12's status line was wrong.** That item says the track is built and *"what remains is
  elapsed time and reading the track, not building it."* The arithmetic below is why that is
  false, and it is unchanged by the session-14 bullet above.
  * **THE ARITHMETIC IS THE FINDING, and it is not escapable by choosing a better statistic.**
    From `benchmarks.spy` the top decile beats SPY by **+9.99%/yr at a tracking error of
    11.4pp/yr** — an **information ratio of 0.88/yr**, and that is the IN-SAMPLE figure. Since
    t grows as √time, **t = 2.0 arrives at 5.2 years** (7.6 once R9's lag-1 +0.189 is applied as
    an n_eff haircut). **At 12 months the power is 18% and the minimum detectable edge is
    +34pp/yr — over three times what the project claims.** If the strategy is exactly as good as
    backtested, a one-year forward test reports "no evidence" **82% of the time**.
  * **REFUTATION TAKES EXACTLY AS LONG AS CONFIRMATION** — the test is symmetric. There is no
    horizon at which bad news is cheap. Nobody may say a short track disproved this either.
  * **THE TRACK CANNOT PRODUCE THE SERIES A VERDICT NEEDS, IN EITHER SOURCE.**
    `paper_index_track` stores a **snapshot of currently-open holdings** measured from each
    name's own entry, not a chained series — differencing two points is not a monthly return, and
    a departed name stops contributing. `paper_track.py:735-740` says so, and says chaining
    closed stints in *"is a construction change, not a bug fix, and was not made."* The Cowork
    file chains correctly but is **missing days** (two rows exist where five were due). **The
    verdict is not computable at any horizon until one source produces a chained series.**
    **PARTLY CLOSED 2026-08-09 (session 14): the snapshot objection was about the ENGINE, and
    the engine is not the bound source.** The Index series stores cumulative-since-inception
    levels, and `track_meter.monthly_excess` chains them into calendar months — a construction
    **robust to an interior missing day**, since a month needs only its two endpoints (pinned by
    `test_an_interior_missing_day_does_not_corrupt_a_monthly_return`). A month whose *month-end*
    mark is missing or >3 trading days stale is **voided**, never silently averaged over. **What
    remains is the missing writer, not the construction.**
  * ~~**THE INCEPTION DATE EXISTS ONLY IN A GITIGNORED FILE.**~~ **CLOSED 2026-08-09 (session
    14).** `2026-07-30` is now in **tracked** files — `PAPER_TRACK_CONTRACT.md` §5 and
    `track_meter.INCEPTION`, pinned by a test. The pre-registration can now be produced by
    anyone with the repo, which is what makes it one.
  * **THE SITE PROMOTES THE TRACK TO ITS HEADLINE BY ITSELF, ON A FIXED DATE, WITH NO APPROVAL
    STEP — THE ONE ITEM HERE WITH A DEADLINE.** `index_track.py:223-224` is
    `thin = days < MIN_LIVE_DAYS` then `headline = "backtested" if thin else "live"`, and
    `MIN_LIVE_DAYS = 60`. At day 60 the *"too early to judge"* pill (`index.html:114`)
    disappears and the headline flips to **live**. **The track is on day 5: this fires ~55
    trading days out, late October 2026, at 13% power (minimum detectable edge +49pp/yr).** The
    **CLOSED 2026-08-09 (`126c137`, engine lane) — see the session-14 bullet above: the flip now
    requires the contract's `Operational gate passed` row as well as the day count, and that row
    reads `pending`.** The rest of this sub-bullet is the record of what the defect was. The
    constant was never pre-committed, does not derive from power, and disagrees 2× with
    `paper_track.MIN_DAYS_FOR_MEANING = 126` governing the same track. ~~Both sit in
    `valuation/screener/index_track.py` — outside the edge lane; it needs assigning.~~
    **CORRECTED 2026-08-09 (session 14): THEY SIT IN DIFFERENT FILES AND DIFFERENT LANES, and
    this sentence was the one assigning the work, so the wrong file name pointed the fix at the
    wrong lane.** `MIN_LIVE_DAYS` is `valuation/screener/index_track.py:44` (engine lane, fixed);
    `MIN_DAYS_FOR_MEANING` is **`valuation/edge/paper_track.py:70`** — the edge lane's, and it
    was a **second ungated door**: `hero` falls back to `paper_track.index_summary()` when the
    Cowork files are absent, which is the fresh-deploy case, and that read a pure day count.
    **Both are now gated on the contract's one row; `index_summary` delegates to
    `index_track.gate_state()` rather than parsing the contract twice, and fails closed.**
  * **STATE, as of this bullet: the track is BEHIND — inception 2026-07-30, five days, Valquo
    +0.78% vs SPY +3.62%, excess −2.85pp.** That is −1.8 SD of a five-day window (p ≈ 0.08),
    i.e. an ordinary bad week that means nothing about the strategy — **but it means the start
    date is being chosen with the sign of the accrued period known**, so discarding those days
    is the flattering direction. `PAPER_TRACK_CONTRACT.md` is a **DRAFT awaiting Don**; zero
    trial cost, equity `N` stays 129, and the trial is charged on sign-off.
- **X8 REPLICATED ON 2026-08-04 AND THIS FILE NEVER RECORDED IT — the single strongest piece of
  external evidence the project has, missing from its own memory for three days (found
  2026-08-07, session 8).** Before this bullet, `CLAUDE.md` contained the words "JKP" and "Japan"
  **zero times**, and `HANDOFF_STATUS.md` likewise; the only trace was the phrase "X8's
  international replication is the out-of-sample evidence, R1 is not", which reads as *future*
  work. **It is not future work.** The omission demonstrably misled: session 8's own prompt
  instructed the agent to "scope X8 … make that actionable instead of aspirational" — for a test
  that had already run and passed. Result, from `HANDOFF_free_analysis.md` (2026-08-04, verdict
  **REPLICATES**, threshold committed first): the untuned 5-theme equal-weighted composite,
  mapped 1:1 onto Global Factor Data with **no tuning of any kind**, monthly `vw_cap`,
  1999-01 → 2025-12, NW(12):
  * **Japan +2.05%/yr (t 3.85)** and **developed Europe +3.36%/yr (t 4.30)** — both clear the
    pre-committed t > 2.0. World ex-US +3.37% (t 5.03). **All 15 European countries positive,
    12 of 15 clear t > 2.**
  * **THE CONTROL IS THE POINT: the USA is the WEAKEST region tested (t 2.35)** — weaker than
    Japan, Europe, developed and world-ex-US. The theme structure is **not** a US artifact, and
    it is out-of-sample in vendor, country, construction and period simultaneously.
  * **REPORTED, NOT BURIED: the composite replicates while its COMPOSITION does not.** Japan's
    result is carried by value (t +2.27) and size (+1.81); **quality (−0.12) and momentum
    (+0.88) contribute nothing there**, the mirror image of the US profile (quality +3.03).
    Momentum failing in Japan is a documented stylised fact, which is evidence the data is real.
    Two of five mapped themes do not generalise to Japan.
  * **IT DOES NOT CORROBORATE VALQUO'S MAGNITUDE, AND MUST NEVER BE QUOTED AS IF IT DOES.** JKP
    earns **+2% to +3.4%/yr long-short at `vw_cap`**; Valquo's long-short is **+20.4%/yr** — a
    factor of six, on a different instrument (capped value-weighted broad factors vs an
    equal-weighted concentrated decile book). **X8 establishes that the premia are real and
    general; X4 says the margin over what a user can buy is not demonstrable since 2014.**
    Together: strong evidence for genuine factor exposure, weak evidence for implementation
    alpha. Only 5 of 7 themes map — `insider` and `institutional` have no analogue, and they are
    the same two X4 found have no retail ETF analogue.
  * **LICENCE: CC BY-NC 4.0, RESEARCH ONLY.** It validates the model and can **never ship in the
    product**. Data lives in `data/factors/research_only/jkp/` (2.1 MB, 17 regions × 324 months,
    already on disk). Reproduce with `python -m scripts.jkp_replication`.
- **WHICH SELECTION RULE PICKS A THEME TO DROP IS NOT ANSWERABLE ON THIS PANEL, AND THE TEST WAS
  DELIBERATELY NOT RUN (2026-08-07, session 8). This is a result, not a skipped task.** Session 7
  ended by nominating a pre-registered test of the *selection rule* (the decide-half argmax picked
  `momentum` and `capital_discipline`, both of which flip sign across halves, while `quality` —
  stable on both halves — was never selected). The answerability question was settled **before**
  anything was run, on the already-published session-7 arm table, so it cost **zero trials**:
  * **A three-block design on 69 dates gives 22-date blocks, and the noise on a 22-date block is
    σ = 1.57pp against a pre-committed margin of 1.00pp.** Pure noise clears that margin **26.1%**
    of the time; power under the record's own best estimates is **50.6%** — a coin flip in both
    directions. A positive result and a negative result would have been equally uninterpretable.
  * **THE DESIGN CANNOT SEPARATE THE TWO RULES EVEN IN PRINCIPLE.** Monte Carlo over the design:
    the stability rule and the incumbent argmax rule **select the same arm 90% of the time** and
    reach a **different verdict on only 5.1% of panels**. The experiment is not merely
    underpowered — it is the wrong shape, because "which rule is better" is a property of the
    distribution over panels and one panel yields one draw.
  * **THE DECISIVE FACT, and it needs no variance estimate: with one panel the paired sign test
    has n = 1, whose smallest achievable p-value is 0.50. No threshold reaches significance, so
    no possible outcome could have been quotable.**
  * **DECLINING KEPT THE DENOMINATOR: equity `N` stays 116** (Deflated Sharpe **0.8674**,
    √(2·ln 116) = **3.083**). Running the 7-arm sweep would have made it 123 → DSR 0.8609,
    √(2·ln 123) = 3.102, purchasing a coin flip with a real haircut. **Not running a test that
    cannot resolve is the cheaper action, not the lazier one.**
  * **~~IT IS ANSWERABLE ON X8's DATA~~ — VOID, REFUTED BY MEASUREMENT 2026-08-07 (session 9).
    THE WORD "INDEPENDENT" WAS AN ASSUMPTION AND IT IS FALSE.** This bullet used to say "16
    held-out countries give 16 independent draws instead of 1; a paired sign test then reaches
    α 3.84% at ≥12/16, with 80% power…". Session 9 built the gate and measured it: see the
    next bullet. **Every number in that sentence is void — the 3.84%, the 80% and the 8.5%.**
- **16 CO-MOVING COUNTRIES ARE WORTH 2 TO 4 INDEPENDENT DRAWS, NOT 16 — SO A "REPLICATES IN N
  COUNTRIES" COUNT IS WORTH FAR LESS THAN ITS N SUGGESTS (2026-08-07, session 9, SELRULE).**
  The cross-country selection-rule test session 8 pre-registered was executed in full. The
  clustering gate (`valuation/edge/cross_country.py`) was built, tested and committed BEFORE the
  measure set was touched; it re-points X7's design-effect-vs-shuffled-null machinery so the
  block is the MONTH and the observations inside it are the COUNTRIES, making the measured ICC
  the average pairwise co-movement. **Two independent kills:**
  * **THE DESIGN CANNOT RETURN A POSITIVE VERDICT AT ALL. Clustering is measurable on 10 of 10
    arm-pairs** (design effects 3.97–8.27 against a shuffled-null p95 of ~1.13), **ρ 0.198–0.484,
    n_eff 1.94–4.03 countries out of 16.** The calibrated critical count is **17 of 16** at the
    pre-committed max ρ, and **even a unanimous 16/16 gives p = 0.0546** (400k draws, se 0.0004).
    At the *median* ρ the bar is 16 of 16 — unanimity or nothing. **The rejection region is
    empty; the design's power at α 5% is zero.**
  * **THE PRE-REGISTERED 12/16 BAR CARRIES A TRUE α OF 28.7%, NOT 3.84% — a 7.5×
    UNDERSTATEMENT.** Building the gate first is the only reason this session did not quote a
    "3.84%" result that was really a 29% one. **That is what the gate is for, and any future
    claim of the form "it replicates in N countries" must now pass it.**
  * **SEPARATELY: `NO CONTRAST` — both rules select `size` on `usa`**, so every paired
    difference is identically zero. Pre-registered as an outcome before the run. **Not a NULL,
    not a tie.** Four of five arms are same-sign across both `usa` halves, so the stability
    constraint does not bind. **HYPOTHESIS ONLY, generated on the decide set: the instability
    that motivated this whole question (4 of 7 arms flip on Sharadar) may be a property of the
    69-date panel's thinness, not of the selection rule** — 324 monthly observations vs 69.
  * **X8's OWN HEADLINE IS UNAFFECTED.** X8 tests each region's premium separately with NW(12)
    errors and never pooled countries into a count, so it never made the independence assumption
    this refutes. **The gate constrains what is built ON TOP of X8, not X8.**
  * **THE SELECTION-RULE QUESTION IS NOW CLOSED ON BOTH AVAILABLE DATASETS.** One panel gives
    n = 1 (session 8); 16 co-moving countries give n_eff ≈ 2–4. That is not an engineering
    defect — it is the amount of independent evidence that exists. **Do not re-open it without
    new data.** Equity `N` 116 → **121** (5 arms, paid as pre-committed): **Deflated Sharpe
    0.8628, √(2·ln 121) = 3.097.** Reproduce with
    `python -m scripts.selection_rule_crosscountry`; `data/free_analysis/SELRULE_CROSSCOUNTRY.json`.
- **THE ML TREE COMBINER IS REJECTED, AND ITS DECILES RUN BACKWARDS OUT OF SAMPLE (2026-08-08,
  session 11, roadmap #16). The register was executed unmodified.** `PREREG_ml_combiner.md` was
  committed blind at `ec6c01d` a session before it ran: seven deployed theme z-scores,
  rank-of-`fwd_ret` target, 63d, the corrected 69-date panel, a FROZEN 8-point
  `HistGradientBoostingRegressor` grid, all selection confined to a decide half via CPCV, one
  measurement per direction, both directions.
  * **WORSE ON ALPHA IN BOTH DIRECTIONS, so REJECTED by the registered rule.** decide-early →
    measure-late: tree **+1.88%** vs linear **+11.58%**, **Δ −9.70pp**, ΔHAC t −2.118.
    decide-late → measure-early: tree **−2.66%** vs linear **+2.82%**, **Δ −5.48pp**,
    ΔHAC t −2.877. All three ADOPT criteria fail in both directions.
  * **THE FINDING IS STRONGER THAN THE VERDICT: the tree's monotonicity is +0.382 and +0.842**
    — remember **negative is well-ordered** — so its top decile underperforms its bottom decile
    out of sample. **The run contains its own control:** the linear arm scored on the IDENTICAL
    rows through the IDENTICAL `quantile_backtest` call is well-ordered (−0.903, −0.855), and the
    equal-weight benchmark matches between arms to four decimals. **It is the model, not the
    harness.**
  * **IT IS NOT A FITTING FAILURE. All 16 grid × direction cells had a POSITIVE decide-half CPCV
    out-of-sample rank IC (+0.011 to +0.024).** The model generalises across 15 purged CPCV paths
    *inside* the decide half and then **reverses across the boundary**. It learns half-specific
    structure strong enough to invert a ranking rather than merely dilute it.
  * **THE TWO DIRECTIONS SELECTED OPPOSITE ENDS OF THE GRID, monotonically.** decide-early ranks
    capacity best-to-worst (most complex wins); decide-late ranks it worst-to-best (least complex
    wins). **Whether model capacity helps is a property of which half you look at, not of the
    problem.** Same shape as session 7's LOO.
  * **QUOTE IT WITH THE PARAM-SEARCH PRECEDENT: +8.43%/yr in-search → −0.04%/yr locked hold-out.**
    The combiner is that phenomenon with a sharper edge. **Selection on this panel does not merely
    fail to generalise; it can generalise backwards.**
  * **WHAT IT DOES NOT SAY:** it does not vindicate the flat 1/7 linear form, it does not close
    roadmap #16 (a raw-signal or different-model-class variant is a NEW pre-registration, and it
    inherits this reversal as its prior), and it changes nothing in the live product.
  * **Trial cost paid as registered: equity `N` 121 → 129, Deflated Sharpe 0.8628 → 0.8556,
    √(2·ln 129) = 3.118.** Every equity claim after this is charged N = 129.
    `data/free_analysis/ML_COMBINER.json`; reproduce with `python -m scripts.ml_combiner`.
- **`N` MOVES THE LONG-SHORT t, AND THEREFORE MOVES THE CALIBRATED FLOORS. THE X7 8%-vs-7%
  DISCREPANCY IS CLOSED — IT IS ONE DRAW, SEED 1005 (2026-08-08, session 12).** Two sessions
  called it undiagnosable because X7's raw draws were never retained. The cause is a coupling
  nothing in the record described: `cpcv_validate`'s adopt gate is
  `margin > _trials_haircut(len(names)) · se`, and `_trials_haircut` (`fundamental_panel.py:2097`)
  is **floored at the research log's `N`** (audit M1); `scripts/placebo.py` then feeds the
  **adopted** weights to `quantile_backtest`. **Adoption is monotone decreasing in `N`, so raising
  `N` re-scores a draw under different weights.**
  * **X7 ran at N = 84 (haircut 2.97685); session 10 ran at N = 121 (haircut 3.09703).** Seed
    1005's margin is **0.00287097** against `se` **0.00094470**: it clears the N = 84 bar
    (0.0028122) and fails the N = 121 bar (0.0029257). Scored under the challenger's weights its
    naive `ls_t` is **2.1273**; under base weights, **1.0454**. Session 10's retained artifact
    records **1.0453572947436582** — identical to the recomputation to sixteen digits.
  * **SEED 1005 IS THE ONLY FLIP IN 100 DRAWS**, which is checkable because the gate's other two
    conditions do not depend on `N`, so adoption is monotone and the search set is the draws that
    did not adopt at N = 121.
  * **IT REPRODUCES EVERY RECORDED NUMBER ON BOTH SIDES.** Substituting the adopted value into
    session 10's 100 draws gives **exactly 8** at `t ≥ 2.0` — X7's figure. And the naive **p95
    stays 2.1437, max stays 3.436** — which is precisely why session 10's control reproduced X7's
    percentiles *to the digit* while missing one draw: **2.1273 lands just below the 95th
    percentile.** One fact explains both halves of what looked like a contradiction.
  * **THE ADOPT CURVE REPRODUCES TWO HISTORICALLY RECORDED RATES THE SCRIPT NEVER SAW.** With
    `(margin, se)` banked, adoption at any `N` is arithmetic: **N = 8 → 27 draws adopt** (X7's
    recorded **27%**), **N = 84 → 21** (M1's recorded **21%**), **N = 116/121/129 → 20**
    (session 10's artifact: **20**), N = 200 → 18, N = 400 → 17. Monotone throughout, and
    **27 → 21 is six draws stopping with none starting** — exactly the one-directional move this
    file records for M1, recovered independently from the margins.
  * **CHECKED, NOT ASSUMED: today's N = 129 still gives 20 adopters, the same as session 10's
    121, so session 10's published floors (naive 2.1437, HAC 2.2837) are still the floors at the
    current `N`.**
  * **IT ALSO EXPLAINS WHY IT LOOKED UNDIAGNOSABLE.** Session 10 reasoned that no draw sat near
    2.0 so it could not be a boundary effect. Correct — seed 1005 did not *drift* across the
    boundary, it **jumped 1.08 of a t** because its weights changed. A knife-edge crossing was
    the wrong thing to look for.
  * **THE CONSEQUENCE THAT OUTLIVES THE DISCREPANCY: A CALIBRATED PLACEBO FLOOR IS A FUNCTION OF
    `N`.** The floor is a percentile of the null `ls_t` distribution, and `N` moves individual
    draws within it. **Here the floors did not move** (2.1437 naive, 2.2837 HAC at both `N`)
    because the one affected draw landed below the percentile — **that is luck, not design.**
    Every sweep must record the `N` it ran at, and **a floor may not be compared across sweeps
    run at different `N` without checking.**
  * **THE SHIPPED STRATEGY IS UNAFFECTED, for a reason already in the record: it does not adopt,
    it keeps `current-default`,** so no haircut touches its `ls_t`. The exposure is entirely to
    the *calibration*, not the headline. Same family as X7's post-hoc "CPCV adoption manufactures
    ~+1.4 of long-short t" — now a demonstrated mechanism on a named draw rather than a split.
  * `cpcv_validate` now banks **`adopt_detail`** (margin, se, haircut, `n_trials_used`) and
    **`challenger_weights_cols`** — the challenger's weights whether or not adopted — so "what
    would this run have scored one haircut lower" is arithmetic. **Zero trial cost**; equity `N`
    stays 129. `data/free_analysis/X7_RECONCILE.json`; `python -m scripts.x7_reconcile`.
- **THE TRIAL COUNTER HAD A REAL DEFECT THAT NEVER FIRED, AND `N` DOES NOT MOVE (2026-08-08,
  session 12).** `research_log._parse` tested `\bFIXED\b` against **every cell of a row joined
  together**, so a row whose hypothesis, threshold, source or note merely contained the word
  "fixed" was dropped from `N` even where its verdict read `REJECTED`. Understating `N`
  **overstates** the significance of every DSR-gated claim — M1's own error, inside M1's own
  parser, carried three sessions. Two sibling defects of the same class were fixed with it: the
  `n=<k>` grid multiplier was grepped from the **whole line**, and the domain came from the first
  cell matching any domain name rather than the domain column.
  * **THE RECOUNT MOVES NOTHING. Equity `N` 129 → 129**, options 164, infra 3, total 296, 57 rows
    counted and 18 dropped (merged log) — identical against the **shipped module itself** and
    against **all fifteen historical revisions** of `RESEARCH_LOG.md`. No `fix*` word appears
    outside a verdict cell in any of the 72 data rows as they stood at the recount; **zero
    near-misses. No published `N` was ever wrong.** Deflated Sharpe stays **0.8556**,
    √(2·ln 129) stays **3.1176**, and all four DSR figures in this file
    (N = 84 → 0.899659, 116 → 0.867360, 121 → 0.862756, 129 → 0.855608) reproduce to six decimals.
  * **THE REPAIR NEARLY SHIPPED THE ERROR IT WAS FIXING, AND THAT IS THE MOST USEFUL THING HERE.**
    Merging `origin/main` mid-session brought in **O16**, which writes
    `|Spearman(term_slope, atm_front)|` — an absolute value — **inside a markdown table cell**.
    The unescaped `|` gives that row **11 cells against a 9-cell header**, shifting every column
    after the metric; the first-cut column parser read `n` off prose and charged it **1 trial
    instead of 5, understating options `N` by 4** — the same harmful direction, in a different
    column, and **the whole-line grep it replaced was accidentally immune**. It was caught only
    because merging and re-running the recount was written into the procedure rather than left to
    the end. Misaligned rows now resolve toward a **larger** `N` and are listed in
    `rows_malformed`. **The O16 row is NOT edited** (the register forbids it); **its pipes want
    escaping as `\|` by the lane that owns them** — it is the only malformed row in 74.
  * **WHY IT NEVER FIRED IS NOT REASSURING.** Sessions 9-11 knew about the defect and dodged it
    by choosing synonyms; the earlier rows avoid the word by luck. **A denominator protected by
    authors' word choice is not protected.** The repair is pinned by a fixture the old parser
    fails (3 real trials, of which it counts 1), and `detail()` ships
    `rows_rescued_by_parser_fix` so a silent revert would be loud.
  * The pre-registered expectation (`N` rises, 60/40) was **WRONG** — five wrong directional calls
    to one right. Procedure committed at `21069ac` before the parser was touched, including the
    rule that **no row's text may be edited to change `N`**: `PREREG_session12_recount.md`.
- **THE COMPOSITE'S COMPLEXITY IS NOT DEMONSTRATED, AND THEME IC DOES NOT PREDICT WHICH THEME
  MATTERS (2026-08-06, session 6, X3 RE-RUN). The 2026-08-03 "EARNS ITS COMPLEXITY" verdict is
  VOID — it ran on the pre-B6 110-date panel and against a 1.0pp bar that sits BELOW X7's
  1.95pp noise floor.** Re-run on the corrected 69-date panel against the calibrated bars,
  8 pre-registered arms, flat weights:
  * **The full seven-theme composite beats its own best single signal (`gp_on_capital`) by
    +4.51%/yr, CI95 [−0.14%, +9.12%] — INCLUDES ZERO, so by the pre-registered rule this is a
    NULL.** A near miss is a null. **But "decoration" is the WRONG word and must not be used:**
    `gp_on_capital` alone posts long-short *t* **0.413** against the composite's **2.836** and
    clears none of X7's bars but the alpha margin. Quote both halves: *"the seven-theme
    composite is the only arm that clears the calibrated long-short bar of 2.14, and its
    top-decile alpha advantage over the best single signal is +4.5pp/yr but not separable from
    zero on 69 periods."*
  * **THE CURVE DOES NOT FLATTEN — IT IS NOT A CURVE.** Alpha by cumulative arm (themes added
    in descending IC order): +1.12 → +0.96 → +3.77 → +4.05 → +3.22 → +4.10 → **+7.17%**. Two
    prefixes have POSITIVE monotonicity, i.e. their deciles run backwards. **Only the full arm
    clears the long-short bar; the best prefix reaches t 1.02.**
  * **THE FINDING TO CARRY: `size` has the WORST theme IC (−0.30) and carries the composite's
    entire statistical significance.** Adding it last takes alpha +4.10% → +7.17% and LS *t*
    1.02 → 2.84. **Ranking themes by IC and adding greedily measures the wrong thing** when a
    theme's value is its orthogonality. This is the P6 lesson ("a signal's IC can be flat while
    the composite built from it moves a lot") in a far starker form.
  * **EXPLORATORY leave-one-out, NO VERDICT, do not act on it:** dropping `capital_discipline`
    (2nd-best IC, one of only two clearing X7's bar) *raises* alpha to +8.54% and LS *t* to
    3.352; dropping `size` costs 3.08pp/yr. Seven correlated comparisons reported for their
    extremes. **Nothing was changed on it.** A pre-registered, held-out LOO is Session 7's
    first item.
  * **THE TRIAL COUNT ROSE AND THE HEADLINE PAID FOR IT. Equity N 84 → 104** (8 new arms plus
    12 from the void run, which had never been logged). **Deflated Sharpe 0.8997 → 0.8789;
    √(2·ln N) 2.977 → 3.048, past the Harvey–Liu–Zhu hurdle of 3.0 for the first time.** Still
    above X7's calibrated floor of 0.72. `BACKTEST_RESULTS.json` picks this up automatically on
    the next full run.
- **THE EQUITY COMPOSITE IS USELESS AS AN OPTIONS VETO, AND THE REASON IS THAT ON THIS UNIVERSE
  IT IS MOSTLY A SIZE SORT (2026-08-06, session 6, U7 — REJECTED).** Join built and pinned
  (most recent rebalance date **strictly ≤** the alert date, tested against its own look-ahead
  variant). **Coverage measured before any verdict: 98.1% of 3,885 alerts, 97.8% of 186 names.**
  * **The bottom decile — the one a veto exists to remove — is the THIRD MOST PROFITABLE
    (+10.64%).** Expectancy by composite decile is U-shaped, not monotone: D1 +18.74%,
    D2 +14.78%, middle −0.46% to +4.9%, D10 +10.64%.
  * **All three pre-registered cells go the wrong way:** bottom-decile veto lift **−0.57pp**
    (CI [−1.49, +0.32], retention 92.7%), bottom-quintile −1.04pp, within-universe decile
    −0.44pp. Retention was never the binding constraint. **It does not demonstrably HURT
    either — every CI straddles zero. The honest sentence is that the composite's bottom decile
    carries no information about which alerts to refuse.**
  * **NO INTERACTION WITH THE ALERT AT ALL.** The identical veto on the five-seed random-entry
    control lifts by −0.49pp; real minus control is **−0.08pp** [−1.02, +0.82]. The composite
    describes the UNDERLYING, not the alert.
  * **MECHANISM:** median market cap rises monotonically across deciles, **$62.7B (D1) →
    $133.5B (D9)** — inside 187 megacaps the other themes are compressed and `size` dominates,
    so the "veto" vetoes a cap bucket, which is a property of the underlying. (D10 sits at
    $106.0B and breaks the pattern; no claim is made about why.)
  * **CONSEQUENCE: DO NOT RUN U1 (composite → options ENTRY) AS WRITTEN.** The audit's own
    argument is that the veto is "strictly the easier bar". The easier bar failed *with a
    mechanism*. Reopen only with a composite built WITHIN the options universe, or with size
    neutralised.
  * **THE PROJECT'S EXPECTATION WAS WRONG AGAIN — FOURTH IN A ROW.** The pre-commitment said
    "I expect the veto to HELP, 60/40". R10, O20, the spread toll and now U7. **Do not reason
    about the direction of an effect in this project; measure it. Writing the expectation down
    first is worth doing precisely because it keeps being wrong.**
- **X8 HAS LANDED AND IT REPLICATES — THE PROJECT'S ONLY OUT-OF-SAMPLE EVIDENCE, AND THIS FILE
  RECORDED IT NOWHERE UNTIL NOW (added 2026-08-07 by the claims audit; landed 2026-08-04,
  `7edf594`, ledger X8 DONE, write-up in `HANDOFF_free_analysis.md`).** Two bullets below still
  say "still ONE panel; **X8's international replication is the out-of-sample evidence, R1 is
  not**" — written as though X8 were pending. It ran. Untuned 5-theme equal-weighted composite,
  themes mapped 1:1 with **no tuning**, on Global Factor Data (JKP), monthly `vw_cap`, matched
  window 1999-01 → 2026-04, bar committed in writing first (NW t > 2.0, 12 lags, in **both**
  Japan and developed Europe):
  * **VERDICT: REPLICATES. Japan +2.05%/yr (NW t 3.85), developed Europe +3.36%/yr (t 4.30),
    world ex-US +3.37% (t 5.03).** Europe is not one country: **all 15 positive, 12 of 15 clear
    t > 2**.
  * **THE STRIKING PART IS THE CONTROL: the USA is the WEAKEST region tested (t 2.35)** — weaker
    than Japan, Europe and world-ex-US. Whatever else is true, **the theme structure is not a US
    artefact.** It is out-of-sample in vendor, country, construction and period simultaneously.
  * **WHAT IT DOES NOT ESTABLISH — carry this with it: MAGNITUDE.** The JKP composite earns
    **+2% to +3.4%/yr** long-short at `vw_cap`; Valquo's own long-short is **+11.04%/yr**
    (`construction.long_short_ann`, corrected panel). Not comparable instruments (capped
    value-weighted broad factors vs an equal-weighted concentrated decile book), but the gap is
    a factor of 3-5 and **nothing in X8 corroborates it.** *(The X8 write-up states the gap as
    "a factor of six" against a Valquo long-short of +20.4%/yr; that figure does not match the
    landed corrected panel, which reads 11.04%. Quoted here from the artifact, not the handoff —
    the direction of the caveat is unchanged either way. Flagged for the free-analysis lane.)*
  * **The composite replicates while its COMPOSITION does not.** Japan is carried by value
    (+2.27) and size (+1.81); quality is **−0.12** and momentum +0.88 there. The US control is
    nearly the mirror image (quality +3.03, momentum +1.69, value +1.01, size +0.87). Momentum
    failing in Japan is a documented stylised fact, which is evidence the data is real rather
    than a defect. An equal-weighted blend is the right structure for that world — a quiet
    vindication of the untuned flat weights.
  * Secondary arm, reported as measured: JKP publishes **terciles**, not deciles, so monotonicity
    is across 3 points and is weaker than the pre-registration promised. 5/5 correct-sign in the
    US, 4/5 in Japan (the exception is `qmj`, consistent with quality's t there).
- **THE THRESHOLDS ARE NOW CALIBRATED — READ THIS BEFORE QUOTING ANY t, IC OR PBO
  (2026-08-05, audit X7). Every bar in this project was a CONVENTION until this run; three of
  the four are too low, and one is at the noise level.** `scripts/placebo.py` shuffles the
  signal within each rebalance date (block permutation: per-date distribution, missingness
  pattern and cross-theme correlation all preserved exactly; `fwd_ret`/`marketcap`/`sector`
  untouched) and pushes 100 draws through the REAL pipeline — CPCV, weight selection,
  quantile backtest, theme ICs, the held-out gate. The harness reproduces the shipped run
  exactly (t 2.83606, alpha 0.071741, PBO 0.73333) before any draw, and the equal-weight
  benchmark is +18.14% on all 100 draws (sd 0.00004), which is the control.

  | bar | as used | CALIBRATED (placebo p95) | how often pure noise clears the OLD bar |
  |---|---|---|---|
  | theme IC t | 2.0 | **2.71** (noise max 3.93) | **39%** |
  | long-short t (naive) | 2.0 | **2.14** (noise max 3.44) | 8% |
  | **long-short t (HAC — the one to quote)** | 2.0 | **2.28** (noise max 3.78) | 8% |
  | top-decile alpha margin | 1.0pp | **1.95pp** | 18% |
  | PBO | <50% | **<19.7%** (placebo p5; noise MEDIAN is 46.7%) | **55%** |
  | Deflated Sharpe | >0.95 | **STANDS** (noise median 0.28) | 2% |

  **RECALIBRATED 2026-08-14 AT `N` = 224 (`MA19`). THE TABLE ABOVE IS X7's, MEASURED AT `N` = 84,
  AND IT IS KEPT BECAUSE IT IS CORRECT FOR ITS OWN REGIME — every one of its bars was reproduced
  from the banked draws to within rounding. TWO OF THE SIX HAVE SINCE MOVED, AND ONE OF THOSE HAD
  BEEN STALE FOR NINE DAYS. Quote the `derived at N = 224` column - and see the `MB31`
  bullet immediately below, which proves those values are STILL CURRENT at the live
  `N` = 234 rather than asking you to assume it.**

  | floor | X7 @ N=84 | session 10 @ N=129 | **derived at N = 224** | moved? |
  |---|---|---|---|---|
  | theme IC t | 2.7072 | 2.7072 | **2.7072** | never |
  | long-short t (naive) | 2.1437 | 2.1437 | **2.1437** | never |
  | **long-short t (HAC)** | 2.2837 | 2.2837 | **2.2837** | **never** |
  | top-decile alpha margin | 1.9532pp | 1.8629pp | **1.8629pp** | at 84→129 |
  | top-decile alpha HAC t | 2.2913 | 2.2913 | **2.0540** | **at 129→224** |
  | PBO (p5) | 19.667% | 19.667% | **19.667%** | never |
  | Deflated Sharpe | 0.7216 | 0.7076 | **0.6637** | **both steps** |

  * **THE COLUMN IS ONE DENOMINATOR BEHIND THE LIVE COUNT AND EVERY PERMUTATION FLOOR IN IT IS
    NEVERTHELESS STILL CORRECT - PROVED ARITHMETICALLY, NOT ASSUMED (2026-08-19, `MB31`+`MB32`).**
    Live `by_domain` reads **equity 234, options 300, infra 15**, so the table's `N` = 224 column
    is stale as a LABEL. It is not stale as a set of NUMBERS, and the reason is `MA19`'s own
    mechanism run forwards: **`N` enters a permutation floor ONLY through the CPCV adopt gate
    `margin > sqrt(2 ln N) * se`**, so a floor can move only when a DRAW FLIPS. That gate is
    arithmetic on `X7RECON`'s banked `(margin, se)` rows, and **the adopt set at `N` = 234 is
    IDENTICAL to the set at 224 - zero draws flip, in either direction.** So the four
    insensitive-so-far floors AND both of the two `MB31` lists as DUE are **provably unmoved
    today**. The rule was verified against the record rather than trusted: margin-passers minus
    the two draws (1031, 1036) that fail an `N`-INDEPENDENT condition reproduces `MA19`'s recorded
    adopt count of 20 exactly.
  * **AND IT COMES WITH A DATED TRIGGER, WHICH IS THE POINT OF DERIVING IT RATHER THAN TABULATING
    IT: the next draw to flip is seed 1003 at `margin/se` 3.319188, and it flips when
    sqrt(2 ln N) exceeds that - i.e. at equity `N` = 247. THIRTEEN TRIALS OF HEADROOM FROM
    TODAY.** Below 247 no permutation floor can move; at 247 a **bounded** re-derivation is owed
    (`MA19` re-scored three draws in ~400 seconds, not a 3.4-hour sweep - `RUN_RULES` rule 9 is
    why it is bounded), and whether any floor then actually moves depends on where seed 1003 sits
    in each statistic's ranking. **Still report the four as INSENSITIVE-SO-FAR and never as
    invariant** - session 12's *"luck, not design"*, and on the alpha HAC floor the luck ran out.
  * **THE DEFLATED SHARPE IS THE ONE EXCEPTION AND IT DOES NOT GET THE ABOVE ARGUMENT.** `sr0` is
    a function of `N` DIRECTLY, so every draw moves at every `N` and the adopt-set proof simply
    does not apply to it. Recomputed: **`sr0` 0.4604580337 -> 0.4627730517** between 224 and 234
    (reproducing the shipped 0.4604580339 to **2.302e-10**, the tolerance `MA19`'s own C10 control
    reported), so `sr0` RISES and **the DSR therefore FALLS**. **The probability itself is
    deliberately NOT restated at 234**: it needs the returns series' skew and kurtosis, and
    assuming normality shifts it by **-0.0319**, an order of magnitude more than the change being
    measured - a fabricated figure would be worse than none. Both the statistic (0.7863) and its
    floor (0.6637) stay labelled **`N` = 224, STALE BY CONSTRUCTION**. **This correction is one
    the map's own test caught in the map itself**, which had first labelled the DSR floor
    "provably unmoved" by inheriting an argument that never covered it.
  * **THE HLZ HURDLE IS THE ONE NUMBER THAT REALLY DID MOVE, AND THE VERDICT DOES NOT.** Equity
    **3.2898772171176964 at `N` = 224 -> 3.3031261300040304 at 234**, so the headline long-short
    HAC *t* of 2.6199 fails it by **0.6832** rather than 0.6700. `clears_hlz_hurdle` is `false`
    at both. **For an OPTIONS claim the hurdle is 3.3794754082179290 at `N` = 302** - quote that,
    never the equity one. **That figure moved WHILE THIS ITEM WAS BEING WRITTEN** - it read
    3.3775086897463940 at `N` = 300 an hour earlier, until `MB1` booked two options trials -
    which is `MB32`'s own thesis demonstrated on `MB32`: the DERIVED map absorbed the change
    with a re-run and this hand-written sentence had to be edited. **Derive it; do not quote
    it from here.** `BACKTEST_RESULTS.json` legitimately LAGS at 224/292/14 per `MA21`
    (trials only accumulate, so the artifact may lag and may never lead) and **needs no re-run
    for this**, since no claim changes side.
  * **THE SENTENCE SHAPE TO KEEP WATCHING, because it recurs automatically: a numerator at one
    `N` paired with a floor at another.** `MA19` caught it once - *"0.8674 vs the 0.7216 floor"*
    pairs an `N` = 116 Deflated Sharpe with an `N` = 84 floor - and the DSR moves at EVERY `N`, so
    the shape regenerates unless the text names the `N` on both sides. The phrase **"at today's
    `N`"** is the same defect in slower motion and was removed from three sites in this file by
    `MB32`: *today* moves, a number does not. `data/free_analysis/MB31_STALENESS_MAP.json` is
    DERIVED (`python -m scripts.mb31_staleness_map`) precisely so this table never has to be
    re-typed again.
  * **NO SHIPPED CLAIM CHANGES ITS RELATIONSHIP TO ITS BAR** — all seven clear (or, for PBO, fail)
    exactly as before, and both moves are in the strategy's favour. **Nothing is retracted.**
  * **THE 1.95pp ALPHA MARGIN WAS STALE AND THE RECORD KEPT QUOTING IT.** The correct figure has
    been **1.863pp** since session 10's own sweep, which measured it, banked it, and published only
    the long-short floors. `RUN_RULES` rule 9 running backwards: **storing the draws is necessary
    and not sufficient — someone has to read them out.** The bar is LOWER, so the correction is
    permissive and `S10`'s "1.0pp sits below X7's 1.95pp" holds a fortiori.
  * **MA19's OWN PREDICTION IS REFUTED and the reason is the portable part.** It expected the
    long-short floors to FALL (fewer adopters → fewer noise draws collecting the ~+1.4 *t* adoption
    bonus). **They did not move by a single bit at either step.** A p95 over 100 draws is set by the
    5th-and-6th largest values, so **whether a floor moves depends not on HOW MANY draws flip but on
    WHERE THEY SAT** — the two that flipped ranked 15th/35th on the long-short statistics and
    **4th** on the alpha HAC *t*, which is exactly the one that moved. **A calibrated floor is a
    STEP function of `N`, and the steps are at the tail.**
  * **THIS IS THE FIRST TIME SESSION 12's WARNING FIRED.** It recorded that the floors surviving an
    `N` change was *"luck, not design"*. On the alpha HAC *t* the luck ran out.
  * **THE DEFLATED SHARPE MOVES BY A DIFFERENT CHANNEL AND BOTH SIDES MOVE:** `N` enters `sr0` in
    the formula itself, so **every** draw moves, not only the flipped ones. **The real statistic
    reads 0.7863 at `N` = 224** (0.8628 at 121, 0.8674 at 116). **A real-vs-floor comparison must be
    made at ONE `N`** — the record's *"0.8674 vs the 0.7216 floor"* pairs an `N` = 116 numerator with
    an `N` = 84 denominator. **At a consistent `N` = 224: 0.7863 vs 0.6637 CLEARS, and vs the 0.95
    convention still FAILS** — the same sentence the record already tells, now internally consistent.
  * **Method:** the adopt SET at any `N` is arithmetic from banked `(margin, se)`, but the FLOORS are
    not — only 1 of 100 banked rows carries both weight-scorings — so **three draws were re-scored**
    on the same panel, seeds and estimator (~7 min, not a 3.4-hour sweep). Eleven controls, two
    gating, all pass; the 98 untouched draws are bit-identical at max |Δ| **0.000e+00**.
    `data/free_analysis/MA19_RECALIBRATION.json`; `HANDOFF_edge_audit.md` MA19+MA13.

  **THE DEFLATED SHARPE ROW IS CONFIRMED AT THE TRUE N (2026-08-06, session 5). The
  PROVISIONAL marking is LIFTED.** The placebo was re-run at `N = 84` on the identical panel
  and identical seeds. **The statistic is MORE discriminating at the honest denominator, not
  less: 0 of 100 noise draws clear 0.95, against 2 at N = 8**, and the calibrated bar (placebo
  p95) falls 0.8567 → **0.7216**. Every OTHER rate in this table is identical to the last digit
  across the two sweeps (holdout 6%, ls_t≥2 8%, maxIC_t≥2 39%, PBO<50 55%), which is the
  harness-reproduction check — so no other calibrated bar was ever in question.
  **BOTH M1 AND X7 ARE RIGHT AND THEY NEVER CONFLICTED.** The edge's 0.8997 fails the >0.95
  convention (M1) **and sits above ALL 100 placebo draws** (max 0.8649, empirical p ≤ 0.01),
  because at the honest N the 0.95 convention is STRICTER than the noise floor requires.
  **Quote it whole or not at all:** *"Deflated Sharpe 0.8997 at N = 84 — fails the conventional
  >0.95 bar, while sitting above all 100 placebo draws (calibrated bar 0.72)."* It is the one
  bar where this strategy is distinguishable from noise and still fails its threshold.
  **M1 also made the adoption gate harder for noise to pass, as a free side effect:** CPCV
  adopts on **27% → 21%** of pure-noise draws, one-directional (six draws stopped adopting,
  none started). ~~because the adopt gate reads the Deflated Sharpe~~ — **THE MECHANISM WAS
  BACKWARDS; CORRECTED 2026-08-08 (session 12). The direction and the magnitude are right and
  the mechanism was not.** The adopt gate cannot read the Deflated Sharpe: adoption is decided
  at `fundamental_panel.py:2729` and `_dsr_detail` is computed at `:2744`, **downstream of it**,
  on the returns of whichever scheme adoption just chose. What M1 actually changed is
  `_trials_haircut` (`:2097`), which is **floored at the research log's `N`** — and the adopt
  gate multiplies `se` by that haircut. Both the haircut and the DSR read `_trial_N()`; neither
  reads the other. **This matters beyond pedantry, because it means `N` MOVES `ls_t`** — see the
  session-12 bullet below. **This is NOT the run-to-run
  non-reproducibility** — that remains open; it was briefly mistaken for it before the
  one-directional pattern was checked.

  **Use these numbers, not the old ones.** They are floors for THIS panel/universe/69 dates,
  not universal constants — re-measure if the panel changes materially. Three consequences
  that are easy to get wrong: **(a)** 39% of noise draws produce at least one theme at IC
  t ≥ 2.0, because EIGHT themes are tested and the bar is applied to whichever looks best —
  the project has always read that bar as if one theme were being tested; **(b)** the
  **held-out gate (`holdout_theme_validate`) has a measured ~6% false-positive rate**, and
  `low_risk` — the theme actually zeroed on its verdict — turned up among the false confirms
  once in 100 draws, so that decision is not overturned but must be quoted with the rate;
  **(c)** the real headline is outside the placebo's [2.5, 97.5] interval on alpha (clearly),
  Deflated Sharpe, monotonicity, max theme IC t (narrowly) and long-short t (narrowly) — and
  **INSIDE it on PBO**, which is therefore not distinguishable from noise.
- **THE OPTIONS ENTRY SIGNAL IS DEAD, ON CORRECTED DATA (2026-08-05, audit session 5 / R2). The
  project's most consequential negative finding was re-derived after five defects were repaired,
  and it SURVIVED — the gap moved 0.61pp.** Every number in `HANDOFF_universe_backtest.md` was
  computed against a mis-stated underlying price (B1) plus B2/B3/B4/B15, and that file is now
  banner-marked SUPERSEDED. Re-run on the identical pinned 187-name universe:
  **CORRECTED 2026-08-11 (session 23, `U1-SPLIT`) — THE GAP IS −5.06pp, NOT −6.65pp, AND 24% OF
  THE PUBLISHED GAP WAS A CORPORATE-ACTION ARTIFACT. THE VERDICT IS UNCHANGED.** The figures
  below now read split-clean; the as-published ones are kept beside them because the
  re-derivation reproduces them **to the digit**, which is what makes the correction checkable.
  Option chains are as-traded and unadjusted for splits while `bars` ARE adjusted, and nothing in
  the options lane consulted the split table — GE's 1-for-8 reverse split (2021-08-02) let a
  $0.27 call settle against a ~$104 post-split underlying on a pre-split strike and book
  **+31,921%** against a true value of **zero**. Full repair record in `PREREG_u1split_repair.md`.

  | | as published | **split-clean (quote this)** |
  |---|---|---|
  | alert book | +3.41%/trade | **+3.2702%** (n 3,885 → 3,870) |
  | five-seed control | +10.06%/trade | **+8.3342%** (n 29,785 → 29,654) |
  | **gap** | −6.6468pp | **−5.0640pp** |
  | date-block CI95 | [−11.9152, −2.1317]pp | **[−8.5957, −1.5325]pp** |
  | paired sign-test z | −4.9027, 1,334 cells | **−4.9612, 1,332 cells (p 7e−07)** |

  **THE CONTROL IS CONTAMINATED ~12× HARDER THAN THE ALERT BOOK** (15 rows vs 131) because it
  draws many random days per name-year and so gets more shots at any split window — two GE draws
  at +269x and +261x. **The defect was therefore making R2's negative verdict look WORSE than it
  is, and correcting it runs TOWARD the alert.** It still loses decisively.
  **REPORTED BECAUSE IT CUTS AGAINST THE OBVIOUS READING: the sign test does NOT weaken — it
  strengthens slightly, −4.9027 → −4.9612.** The mean gap shrank because the artifact was a
  right-tail phenomenon in the control; the median name-year cell never depended on it. The
  alert's day-selection subtracts value. **Do not describe the live options alert as a
  day-selection edge; it is an alert-generation mechanism.**
  * **THE BREADTH CLAIM IS VOID.** "The edge survives breadth but roughly halves" is false.
    **CORRECTED 2026-08-11 (`U1-SPLIT`): split-clean the new names read −0.5589%/trade and the
    baseline 54 megacaps +9.1391%** (as published: −0.4713% and +9.3720%, reproduced exactly).
    **The count is 132 names, not the 133 this file has said** — `UNIVERSE_RESULTS.json`'s
    `new_names_only.n_names` has always read 132. All of the book's positive expectancy is still
    the original 54 megacaps, so the claim's substance is unchanged. It is a megacap phenomenon
    that a corrupted price basis made look broader.
  * **B1's signature, for the record:** trades ROSE 3,042 → 3,885 because `no_contract_in_band`
    rejects fell 2,911 → 1,729 — an adjusted spot against as-traded strikes was throwing the
    0.90–1.20 moneyness prefilter, silently discarding 1,182 alerts. Median entry IV
    **1.4200 → 0.2497** at 100% coverage (was 75.3%). 142% was never a vol.
  * **A SINGLE CONTROL SEED CAN FLIP THIS VERDICT — RUN FIVE, AND READ THE SIGN TEST.** The
    control's own mean ranges **+6.46% to +15.34%** across five draws. Seed 0 alone reads
    INCONCLUSIVE and is the most favourable of the five; **all five point estimates are
    negative and four of five are negative at significance.** A random-day book's mean on a
    barbell payoff is set by a few +600% trades. **More control draws SHARPEN the test** (2-seed
    z −2.907 → 5-seed z −4.903), because each name-year cell's control mean averages more draws.
    The paired *t* ranges +0.162 to −1.835 and is never significant even pooled (−1.227, p 0.22)
    — it is the wrong statistic here. **Standing rule: five seeds minimum, sign test carries the
    verdict.**
  * **`term_slope` is REJECTED on the arm that matters (R7).** Its +8.89pp out-of-sample
    replication was an artefact; corrected, the filter makes its own out-of-sample book WORSE
    (gain **−1.12pp** against a +5.00pp bar) and is no longer tail-enriching. It PASSES the
    re-committed retention floor (G3a 95.6 alerts/yr, G3b 96.2% of names and 98.2% of months,
    G3c 35.9%) — so the old 40% constant WAS rejecting a genuinely broad filter, and the
    rejection now rests on economics instead of on an underived number.
  * **Deflated Sharpe fell below 95% on both books:** unfiltered 88.13% → **49.59%**,
    term_slope-filtered 95.69% → **80.63%**. The autopsy re-confirms: 64 features, 127
    hypotheses, **zero survivors**.
- **OPTIONS STATISTICS ARE CLUSTERED, BUT LESS THAN THE AUDIT PREDICTED (2026-08-05, audit R3).**
  Every options interval ever published resampled TRADES and is optimistically narrow.
  `valuation/edge/options_stats.py` adds a date-block bootstrap (calendar months resampled
  together), `n_eff`, the paired name-year sign test and paired *t*, purge/embargo for the CSCV
  splits, and the Deflated Sharpe at `n_eff`. **CORRECTED 2026-08-06 (session-5 closeout): the
  clustering factor is 2.212, NOT 1.85, and it is INSIDE the audit's predicted 2–4 — the record
  said the audit over-predicted and the record was wrong.** The 1.848 (null p95 1.266) was
  measured on the PRE-CORRECTION 3,042-trade book and never updated; the corrected 3,885-trade
  book gives **design effect 2.2121 against null p95 1.2037**, which is what
  `UNIVERSE_RESULTS.json` has always shipped — the artifact was right, the prose was stale.
  **CORRECTED 2026-08-11 (`U1-SPLIT`): split-clean the figures are design effect 2.1837 against
  null p95 1.1898** — clustering is still measurable, the √-haircut is 1.478× rather than 1.487×,
  and no verdict moves. Removing 15 of 3,885 trades was never going to shift an ICC materially,
  and it did not; the figures are restated only so the file quotes one book throughout.
  **Every options *t* shrinks by √2.212 = 1.487×, not 1.36×**, and **no verdict changes** (checked,
  not assumed: R2 rests on the name-year sign test, the date-block intervals embed clustering by
  construction rather than applying the design effect as a haircut, and
  `deflated_sharpe_clustered` ships alongside the raw figure rather than replacing it).
  * **R3.3 is the one that mattered:** the paired sign test and paired *t* the entire options
    conclusion rested on existed in NO shipped file. They now reproduce the record exactly
    (441 of 1,052 cells, z −5.185 against the recorded −5.24; seed-0 paired t −2.6701 against
    −2.67), pinned by a test.
  * **A RAW DESIGN EFFECT IS NOT EVIDENCE OF CLUSTERING.** Found by a failing test: 600
    independent draws in 12 blocks of 50 report a design effect near 1.8 — pure sampling error
    in MSB/MSW, since that ratio is F(k−1, n−k). Applying it as a haircut would manufacture a
    correction out of noise. The design effect is now scored against its own shuffled null (the
    X7 method) and `clustering_measurable` gates it; the real book passes clearly (**corrected
    book: deff 2.2121 vs null p95 1.2037**; the pre-correction book's 1.848 vs 1.266 is what the
    record used to quote here). **Never quote a design effect without its null — and never
    without its BOOK: that is exactly how the 1.85 figure travelled out of scope.**
- **POINT-IN-TIME LIQUIDITY RAISES THE OPTIONS HEADLINE — the audit expected it to fall
  (2026-08-05, audit O20).** Applying the miner's own screen at each entry date instead of to the
  name's first cached year: **PIT-liquid 3,359 trades at +4.82% vs PIT-illiquid 495 at −7.84%**,
  coverage 99.2%. **CORRECTED 2026-08-11 (`U1-SPLIT`): split-clean these read 3,347 at +4.7293%
  and 494 at −8.0168%** — the means reproduce as published to the digit and the correction moves
  them by hundredths, so nothing here changes. **But it does NOT rescue the signal** — the
  control is screened by the same rule and benefits too, so on the liquid subset the real book
  loses to random entry MORE decisively (z −3.475, p 0.0005). The headline stays the whole book
  at aggression 1.0.
  **THE z OF −3.475 DID NOT REPRODUCE AND IS THEREFORE NOT RESTATED (2026-08-11, `U1-SPLIT`).**
  Re-deriving the liquid-subset paired name-year sign test against the same-screened control
  gives **−4.8953 as published** and −4.8109 split-clean, not −3.475, on a construction that
  reproduces every other O20 figure exactly. The −3.475 is in no shipped artifact —
  `UNIVERSE_RESULTS.json`'s `o20_point_in_time_liquidity` block carries no z at all — so it
  cannot be reconciled from the repository, only re-derived by the lane that produced it.
  **Neither number is quoted as the corrected one here**; the discrepancy is recorded instead,
  because silently substituting a figure that happens to agree in direction is how the 1.85
  design effect travelled out of scope. **Owner: the O20 lane.** The direction of O20's claim —
  the liquid subset loses to its own control more decisively, not less — holds on every
  construction tried.
  **The audit's premise is half wrong and this is the correction:** names were ranked into the
  mining pool by TODAY's market cap (true), but the liquidity screen was already applied to the
  FIRST CACHED YEAR, not to a present-day chain (`mine_options_cache.py:160`). So O20 is an
  UPPER BOUND on the repair — names that would have failed in 2016 were never mined and no
  evaluation-time filter recovers them.
  **THE PATTERN WORTH KEEPING:** this is the third time in two sessions (R10, then O20) that a
  bias the record assumed ran in the strategy's favour ran the other way. **This project's
  expectations about the direction of its own biases have been wrong more often than right.
  Measure them; do not reason about them.**
- **THE EDGE DOES NOT CLEAR THE DEFLATED SHARPE BAR (2026-08-05, audit M1). The last bar the
  project claimed to clear fails once the denominator is honest.** Every multiple-testing claim
  was computed against `N = 8` — the eight weight schemes. `RESEARCH_LOG.md` is now populated and
  `valuation/edge/research_log.py` feeds the real count into `_deflated_sharpe` and
  `_trials_haircut`. Trial counts **as of this bullet**: equity 84, options 139, infra 1, total 224
  (session 5 added 4 options rows), against the audit's ~146 estimate; `FIXED` correctness rows
  correctly do NOT count. **CORRECTED 2026-08-07 (claims audit): those counts are STALE — measured
  today `research_log.detail()` reads equity 116, options 155, infra 1, total 272 (51 rows counted,
  17 `FIXED` rows not counted). `N` is a project quantity that keeps rising; quote the equity 116
  and the 0.8674 from the session-7 bullet below, not the 84 in the table that follows.** The table
  is kept as the record of what M1 measured on the day it landed.

  | | N = 8 (as shipped) | **N = 84 (measured)** |
  |---|---|---|
  | Deflated Sharpe | 0.9970 | **0.8997** — FAILS the >0.95 bar |
  | `sr0_benchmark` | 0.242 | **0.406** |
  | `metric` self-report | `probabilistic_sharpe_ratio_UNDEFLATED` | **`deflated_sharpe_ratio`** |
  | `_trials_haircut` | 2.04 | **2.977** |

  **There is a real win inside the failure: audit B9 is RESOLVED by measurement.** B9 argued the
  statistic was an undeflated PSR because `sr0` collapsed. With a real `N` it does not collapse —
  `sr0` rises to 0.406 against a per-period Sharpe of 0.550, deflating away 74% of it, and the
  statistic self-reports as a genuine Deflated Sharpe **for the first time**. The price of fixing
  it is that the bar is no longer cleared. That trade was pre-committed before the run.
  Also: **√(2·ln 84) = 2.977**, i.e. the multiple-testing haircut at the real `N` lands within
  0.03 of the Harvey–Liu–Zhu hurdle of 3.0 — exactly as the audit predicted.
  **`N` is domain-scoped** (the equity composite is charged the 84 equity trials, not the 218
  project-wide ones — the options autopsy is a different search for a different product), and a
  missing log degrades to `N = 8`, i.e. to the OLD behaviour, never to an unpenalised one.
- **THE HEADLINE NOW HAS A t, AND THE LONG-SHORT t IS 2.620 NOT 2.836 (2026-08-05, audit R9).**
  `top_decile_alpha` — the number on the front of the product — shipped with **no significance
  statistic of any kind**. It now carries **t +4.517, HAC t +4.376, hit rate 71.0%**. The
  long-short's naive i.i.d. t is joined by **HAC t +2.620** and a Ljung–Box diagnostic.
  **Ljung–Box rejects independence at p = 0.036** (lag-1 autocorrelation +0.189), so per the
  pre-commitment **the Newey–West t is now the number this project quotes** and the naive t is a
  diagnostic only. The 63d windows genuinely do not overlap — that dimension was fine — but
  factor spreads are autocorrelated and nothing anywhere measured it. Note the long-ONLY object
  is far better measured (t 4.38) than the long-short the project has always led with.
  ~~Comparing 2.620 to X7's calibrated floor of 2.14 is apples-to-oranges~~ — **CLOSED
  2026-08-07 (session 10). The floor is now measured on the HAC statistic: 2.28, and the
  headline clears it.** See the next bullet; quote **2.620 vs 2.28**, never 2.620 vs 2.14.
- **THE LONG-SHORT FLOOR IS NOW CALIBRATED ON THE STATISTIC THE PROJECT ACTUALLY QUOTES —
  THE HEADLINE STILL CLEARS, AND THE MARGIN ROUGHLY HALVES (2026-08-07, session 10).** X7
  calibrated 2.14 on the *naive* t; R9 then made the *HAC* t the number quoted, and the two had
  been compared to each other ever since. Re-run of X7's placebo — **same panel, same seeds
  1000–1099, same instrument, n = 100, costs measured; the only change is that the recorder now
  stores the HAC statistic `quantile_backtest` had been computing on every draw since R9 and the
  writer was silently dropping.**
  * **CALIBRATED HAC FLOOR (placebo p95) = 2.2837** (noise median 0.121, max 3.783).
    **Shipped HAC t = 2.61991 → CLEARS**, empirical p **0.03** (3 of 100 noise draws exceed it).
  * **BOTH MOVES GO AGAINST THE STRATEGY AND THE CUSHION HALVES.** The HAC floor is *higher*
    than the naive floor (2.28 vs 2.14) while the real HAC t is *lower* than the real naive t
    (2.620 vs 2.836), so the margin over the floor falls **0.692 → 0.336**. It clears; it clears
    by less than the record implied.
  * **THE OLD MISMATCH WAS MILD, NOT WILD: pure noise clears 2.14 on the HAC statistic 6% of
    the time** against the 5% the bar intends. Worth closing, not a scandal.
  * **THE CONTROL REPRODUCES X7 TO THE DIGIT:** naive p95 **2.1437** → X7's 2.14, noise max
    **3.4360** → X7's 3.44. **One discrepancy, reported not buried:** the `ls_t ≥ 2.0` rate comes
    back **7%** against the recorded **8%** — a single draw, with no draw anywhere near the 2.0
    boundary (nearest 1.885 and 2.067), so it is not rounding. **It cannot be reconciled because
    X7's raw draws were never saved.** This sweep saves all 100.
  * **FREE BY-PRODUCT, and it is the stronger number: the top-decile alpha HAC t now has a floor
    too — 2.2913 — and the shipped +4.376 sits ABOVE ALL 100 NOISE DRAWS (empirical p 0.00).**
    **RECALIBRATED 2026-08-14 (`MA19`): this floor is 2.0540 at `N` = 224 — the ONLY X7
    floor to move on the adoption channel, because the draw that stopped adopting sat 4th of 100
    on this statistic and 15th on the long-short one. The shipped +4.3762 still sits above all 100
    draws, so the claim is unchanged and only the bar moved (downward, i.e. easier).**
    **STILL 2.0540, AND PROVABLY UNMOVED AT EVERY EQUITY `N` BELOW 247 (2026-08-19, `MB31`) — proved rather than
    assumed: the adopt set is identical at 224 and 234, and it cannot change before
    equity `N` = 247.**
    The long-ONLY book remains far better measured than the long-short the project leads with.
  * **R9's autocorrelation finding is corroborated:** Ljung–Box on noise draws has median
    p 0.406 and rejects at 7%, i.e. near nominal — so the real series' p 0.036 is a property of
    the real series, not an artefact the pipeline manufactures.
  * Artifact `data/free_analysis/PLACEBO_HAC.json` (all 100 draws retained); procedure
    pre-committed in `PREREG_session10_hac_floor.md`; **zero trial cost** — a calibration
    searches nothing, equity `N` stays 121.
- **THE UNINVESTABLE BENCHMARK WAS THE HARDEST ONE — the expectation was WRONG in the strategy's
  favour (2026-08-05, audit R10).** Alpha had only ever been measured against an equal-weighted
  average of every name in the panel, charged zero trading cost while the strategy pays. Both the
  audit and this session's own pre-commitment predicted that flattered the product. It does not:

  | benchmark | benchmark /yr | top-decile EXCESS /yr | HAC t |
  |---|---|---|---|
  | equal-weight universe (incumbent, cost-free) | +18.14% | **+7.17%** | +4.376 |
  | equal-weight, charged the strategy's own costs | +16.10% | +9.21% | +5.685 |
  | cap-weighted panel average | +14.85% | +10.46% | +4.292 |
  | **SPY total return** | +15.32% | **+9.99%** | +3.770 |

  Over 2009-01 → 2026-01 the equal-weighted panel returned **+18.14%/yr vs SPY's +15.32%** — a
  ~1,500-name equal-weighted book beat the cap-weighted index over a window starting at the
  post-GFC bottom. So the incumbent benchmark is uninvestable in the direction of being **too
  demanding**. **Keep publishing +7.17% as the headline** — it is the most conservative and the
  one every historical figure used, so changing it would break comparability for a number that
  only moves the flattering way. The edge now also survives an INVESTABLE benchmark: +9.99% over
  SPY (HAC t 3.77). Charging the equal-weight book the strategy's own cost table costs it
  2.04pp/yr, a genuine thumb on the scale that had sat in the strategy's favour and is now gone.
  All four ship in the `benchmarks` block on every run.
- **CPCV WEIGHT ADOPTION MANUFACTURES ~+1.4 OF LONG-SHORT t OUT OF NOTHING (X7, post-hoc —
  treat as a strong hypothesis, not a settled result).** Splitting the 100 placebo draws on
  whether CPCV adopted: when it did NOT (73 draws) mean long-short t is **−0.065** (se 0.119),
  a textbook null; when it DID (27 draws) mean t is **+1.343** (se 0.184) and mean alpha
  +0.82pp. It fires on **27% of pure-noise draws**. Mechanism: the adopted weights are chosen
  on the same panel the headline is then measured on. **The shipped strategy is UNAFFECTED —
  it does not adopt, it keeps `current-default`** — which is measured support for the existing
  rule that a CPCV rejection means keep the defaults. But any future run that DOES adopt a
  CPCV scheme has an optimistically biased headline unless measurement moves off the
  selection panel. Not pre-registered; wants a pre-registered replication.
- **CORRECTED 2026-08-03 (audit B9) — TWO OF THE THREE "statistical bars" MEASURE SOMETHING
  NARROWER THAN THE CLAIM THEY SUPPORT. Lead with the long-short t of 3.52 against the
  Harvey–Liu–Zhu hurdle of 3.0. That one is real.** The other two:
  * **DO NOT FOLLOW THAT INSTRUCTION — CORRECTED 2026-08-15 (`MA5`), AND BOTH HALVES OF IT ARE
    NOW WRONG.** The **3.52** is the void pre-B6 panel (live long-short HAC *t* is **2.6199**),
    and **there is no 3.0 hurdle** — the bar is √(2·ln N), which reads **3.2899** at today's
    equity `N` = 224, so the headline **FAILS** it by 0.66 (`R4`). The sentence therefore points
    at the project's most-failed bar and calls it the one that is real. **Lead instead with the
    top-decile alpha HAC *t* 4.3762 against X7's calibrated floor (2.0540 at `N` = 224), which
    sits above all 100 placebo draws**, and quote the HLZ comparison only with R4's
    counter-argument attached. The bullet is kept because it is the record of what B9 found.
  * **The Deflated Sharpe IS deflating — the audit's mechanism for this one is REFUTED by
    measurement, and only half of its criticism survives.** The audit argued that the eight
    weight schemes are indistinguishable (out-of-sample median ICs spanning +0.061 to +0.062),
    so the cross-trial VARIANCE of Sharpes is ~0, `SR₀ ≈ 0`, and the statistic degenerates to
    Φ(SR·√(n−1)). **Measured on the full-universe run: `var_sr_across_trials` = 0.0276 (sd
    0.166, not ~0) and `sr0_benchmark` = 0.242 against a per-period Sharpe of 0.606** — the
    benchmark is deflating away 40% of the Sharpe. The audit inferred near-identical trial
    SHARPES from near-identical median ICs; those are different quantities, and the Sharpes are
    genuinely dispersed. It saturates because a per-period Sharpe of 0.61 over 110 periods is
    a large z, not because nothing is deflated. Every run now ships
    `deflated_sharpe_detail` (`sr0_benchmark`, `var_sr_across_trials`, `n_trials`) plus a
    `metric` field that reads `probabilistic_sharpe_ratio_UNDEFLATED` **if** `sr0` ever does
    collapse — so this is now a measured property of each run rather than an assumption in
    either direction.
  * **What DOES survive: `N = 8` is not the number of trials this project has run.** The
    ledger records of the order of 146 pre-registered tests. That criticism is untouched by
    the above and is the real one. Until a genuine trial counter exists (audit M1,
    `RESEARCH_LOG.md`, started but deliberately not wired), the deflated figure is computed
    against a denominator that is roughly 18x too small.
  * **PBO 6.7% scores the WEIGHT-SCHEME SELECTION STEP ONLY** — "the best of eight nearly
    identical weightings generalises". It says nothing about the ~146 signal-inclusion,
    theme-membership, universe, standardisation and construction decisions in the ledger, and
    the shipped strategy keeps `current-default` anyway, so the selection being scored is one
    the model never makes. Now shipped as `pbo_scope`.
  * The honest version of both needs a real trial counter (audit M1, the append-only research
    log). **Not done.** At N ≈ 100+, √(2·ln N) ≈ 3.0 — about the Harvey–Liu–Zhu hurdle.
- **B8 IS FIXED (2026-08-06, session 7), AND `low_risk` SURVIVES IT ON HALF THE EVIDENCE THE
  RECORD CLAIMED.** `holdout_theme_validate`'s docstring described a clean protocol — flag a
  theme on one half with a pre-specified rule, then measure removal ONLY on the other half — and
  the code never implemented step 2: `rule_fired` was computed and never read. (Line cite, current
  2026-08-07: it is set at `fundamental_panel.py:3576` and now READ at `:3594`, which is the fix.
  This bullet said `:3545` and the long-cited `:3048` had drifted into an unrelated function —
  **line numbers in this file rot within days; re-resolve before trusting one.**) Two verdicts now
  ship, named for what they are:
  * **`verdicts` / `stability_verdicts` — SEMANTICS DELIBERATELY FROZEN.** This is the
    both-halves check every shipped decision actually rested on, and **X7's measured ~6%
    false-positive rate was calibrated against this exact object** (`scripts/placebo.py:108`
    reads this key). Redefining it in place would have left that 6% describing a gate that no
    longer exists — the same class of error as the stale theme IC table.
  * **`oos_verdicts` — the documented rule enforced.** A direction counts only if its decide
    half flagged the theme. `oos_directions_tested = 0` means **no out-of-sample test was run
    at all**, which is a different statement from a negative result.
  * **NEITHER SHIPPED DECISION CHANGES:** `low_risk` `confirmed_oos`, `insider` `rejected_oos`.
    **But `low_risk` is confirmed in ONE of two directions, not two** — the rule fires only on
    the early half. Quote it whole: *"zeroing `low_risk` is confirmed out-of-sample in one of
    two split directions, and passes a both-halves stability check in both."*
  * **THE PART THAT GENERALISES: three themes (`quality`, `capital_discipline`,
    `institutional`) are `not_flagged` in both directions**, because the rule is `median IC ≤ 0`
    and their ICs are positive. `capital_discipline` is precisely the theme session 6's
    exploratory LOO nominated for dropping. **An IC-gated rule cannot express a
    marginal-contribution hypothesis** — X3's whole finding is that theme IC does not predict
    marginal contribution. Do not reach for `holdout_theme_validate` to adjudicate an ablation.
- **THE FULL-SAMPLE LEAVE-ONE-OUT DOES NOT SURVIVE A TIME SPLIT — SESSION 6'S EXPLORATORY
  RESULT IS NOT A PROPERTY OF THE PANEL (2026-08-06, session 7, LOO — NULL).** Pre-registered
  at `5a27ea1` before any number existed: select the best of seven leave-one-out arms on a
  decide half, measure only that arm on the held-out half, both directions, against the
  MIN_HOLDOUT margins committed before P6 (100bps alpha, 0.25 t).
  * **Direction 1 selects dropping `momentum` (decide +3.68%) → measure −1.30%, LS t −0.706.
    Direction 2 selects dropping `capital_discipline` (decide +2.20%) → measure +0.20%,
    LS t −0.201. Neither clears either margin; different themes selected. VERDICT NULL.**
  * **FOUR OF SEVEN ARMS CHANGE SIGN BETWEEN HALVES** (`momentum`, `insider`, `value`, and
    `capital_discipline` moves 3rd → 1st). Session 6's "+8.54% from dropping
    `capital_discipline`" is the average of +0.20% and +2.20% — carried by the late half.
    **Do not quote a full-sample ablation arm as a finding.**
  * **`size` IS CORROBORATED: it is the WORST arm to drop in BOTH halves independently
    (−2.64%, −3.46%)** — the only theme whose LOO effect is both large and stable. Stated with
    its limit: `size` was never *selected* (the rule takes the maximum), so this is the most
    stable cell in a table that carries no verdict, not a pre-registered result. Enough to say
    **"do not drop `size`, and stop treating its low IC as evidence against it."**
  * **NOT CLAIMED, DELIBERATELY:** `quality` clears both margins on both halves and was
    selected in neither direction, because the pre-registered rule takes the maximum and the
    maximum is the statistic most inflated by noise. Promoting that now would be selecting the
    RULE on the results — session 6's error one level up. Session 8 pre-registers it or nobody
    quotes it.
  * **The expectation was written down first and was RIGHT** (NULL at 70/30), breaking a
    four-run streak of wrong directional calls. One correct call after four wrong ones does not
    license reasoning about direction; keep measuring.
  * **Equity `N` 104 → 111 from this session's 7 arms, then → 116 once a concurrent lane's 5
    equity trials merged. QUOTE 116: Deflated Sharpe 0.8674, √(2·ln 116) = 3.083** (still far
    above X7's 0.7216 floor, still below the 0.95 convention). **`N` is a PROJECT quantity, not
    a session one** — it is now two sessions running that the realised count overshot its own
    pre-commitment, for a different reason each time. Also settled this session:
    **`SUPERSEDED` rows DO count toward `N`** — the schema prose said otherwise and
    `research_log.py` never implemented it; the counter is right and the prose is fixed.
- **SUPERSEDED 2026-08-04 (audit session 2, B6) — EVERY NUMBER IN THE NEXT TWO BULLETS WAS
  MEASURED ON A PANEL WHOSE FIRST THIRD HAD AN INVERTED UNIVERSE. The corrected numbers are
  WORSE and TWO OF THE THREE BARS NOW FAIL. Read the "CORRECTED PANEL" bullet below first;
  the two bullets that follow are kept only as the record of what the defect was producing.**
- **CURRENT FULL-UNIVERSE NUMBERS (2026-08-04, after the audit's Part I corrections):
  long-short t 3.884, top-decile alpha +11.78%, monotonicity −0.988, PBO 13.3%.** Measured
  against a clean pre-audit baseline re-run on identical data (t 3.520, alpha +11.88%,
  monotonicity −0.952, PBO 6.7%): the composite sorts BETTER, top-decile alpha is a rounding
  change, PBO doubles off a low base. The equal-weight benchmark did not move (+16.55% in every
  run), which is the control. **Thirteen corrections and NOT ONE held-out verdict changed** —
  the record's decisions were not resting on the defects, and the defects were not hiding a
  different model. The sanity layer's flag count fell 5 → 2 (the three negative-multiple sign
  flags cleared). Full A/B in `HANDOFF_edge_audit.md` Part 2.
- **The edge clears PBO 13.3% (want <50%), long-short t 3.851 (want >2), top-decile alpha
  +11.69%.** The single biggest driver was zeroing `low_risk`, which passed the both-halves test
  described above (decide on one half, measure on the other, both directions). On the
  pre-registered direction the rule fires on the early half (median IC −0.0308) and, measured
  on the later half, **long-short t goes 0.97 → 2.56 and top-decile alpha +6.09% → +9.30%**; the
  reverse direction agrees more strongly (t 0.55 → 2.57, alpha +6.63% → +14.49%). Do not treat
  the edge as settled — caveats at the end.
- **CORRECTED PANEL, 2026-08-04 (audit session 2, B6+B7+B13) — THESE ARE THE LIVE NUMBERS.
  Long-short t 2.836, top-decile alpha +7.17%, monotonicity −0.891, PBO 73.3%, over 69
  rebalance dates on a genuine 18.5-year window (2008-01-16 → 2026-07-24).** The equal-weight
  benchmark moved +16.55% → +18.14%, which is the control and confirms the universe itself
  changed. **CORRECTED 2026-08-05 (audit session 3, X2+X7) — THE "TWO OF THREE BARS FAIL"
  READING WAS WRONG, IN BOTH DIRECTIONS, AND BOTH ERRORS CAME FROM UNCALIBRATED BARS MEASURED
  ON ONE ARBITRARY GRID.** It used to say: "t 2.836 is BELOW the Harvey–Liu–Zhu hurdle of 3.0
  it used to clear, and PBO 73.3% is far above the <50% bar." Both halves are now retired:
  * **t 2.836 vs the 3.0 hurdle is a GRID ARTEFACT.** X2 re-ran the whole backtest on seven
    equally valid rebalance grids (offsets 0/5/10/20/30/40/50 trading days; the grid always
    started at a hard-coded TD=252 and 62 other grids existed that nobody had ever looked at).
    All seven keep 69 dates over the identical window. **Long-short t ranges 2.703 → 3.517,
    median 2.926, and CLEARS 3.0 on three of the seven.** Quote **"t 2.7–3.5 depending on
    grid, straddling the hurdle"** — never one side of 3.0 as a fact.
    **CORRECTED 2026-08-15 (`MA5`): "3.0" IS NOT THE HURDLE AND NEVER WAS — it is √(2·ln N)
    frozen at N = 90. THE COUNT DOES NOT MOVE, AND THAT WAS CHECKED RATHER THAN ASSUMED: the
    seven grids are 2.703 / 2.836 / 2.850 / 2.926 / 3.374 / 3.410 / 3.517, and EVERY hurdle this
    project has ever had — 2.9768 (N = 84, X2's own regime), 3.0, 3.0478 (N = 104), 3.0834
    (N = 116) and 3.2899 (N = 224, today) — falls in the empty gap between 2.926 and 3.374. So
    "three of the seven" is right at every N to date, by luck of where the draws sat rather than
    by design. It first becomes FOUR-of-seven-fail at equity `N` > 296.5, which is roughly 70
    trials away. Session 12's warning applies here exactly as it does to the placebo floors: a
    bar that is a function of `N` may not be quoted across regimes without checking.**
  * **PBO <50% IS NOT A BAR AT ALL.** X7's placebo puts the MEDIAN PBO on a definitionally
    worthless signal at **46.7%**, i.e. the "<50%" bar sits exactly at the noise level and has
    almost no power. Calibrated bar is the placebo 5th percentile, **19.7%**. PBO is
    uninformative here in either direction — do not cite it as a pass or a fail.
  * **Top-decile alpha is the one headline that PASSED its robustness test:** spread across
    the seven grids is only **1.30pp** (median **+7.52%**, range +6.84% to +8.14%), against an
    equal-weight benchmark that itself moved 2.08pp across the same grids. The signal-driven
    number is steadier than the market-driven one it is measured against.
  Only the Deflated Sharpe still passes as originally stated — and X7 now DEFENDS it
  (see the calibrated-thresholds bullet below); per B9 the surviving criticism of it is the
  trial denominator, not the statistic.
  **ATTRIBUTED, one change per run, on the full universe — B6 IS ESSENTIALLY THE WHOLE DROP:**
  reverting B6 alone (B7+B13 still fixed) restores t 3.733, alpha +11.36%, PBO 26.7% at 110
  dates, so **B6 costs t −0.897, alpha −4.18pp and PBO +46.7pp — 100% of the PBO blow-out, 88%
  of the t drop, 89% of the alpha drop.** **B7 alone is NULL on the headline** (t −0.010, alpha
  +0.01pp, PBO and equal-weight unchanged to the digit) — a correctness fix with no performance
  consequence, which is the ideal outcome for one. **B13 alone is small and points both ways**
  (t +0.122, alpha −0.51pp, EW −0.24pp): dropping 384 penny names helps the long-short and costs
  the long-only book, consistent with penny names contributing at both ends of the ranking.
  **What this means: roughly 40% of the top-decile alpha was coming from the 41 early rebalance
  dates at which every name present was one that had already stopped trading.** State it as a
  hypothesis, not a finding — a repair's effect on a fitted statistic is not evidence about the
  repair. Costs still clear comfortably: breakeven 134 bps one-way against a **measured** 33.4
  bps realised (B11 — the old "37 bps" was an assumption quoted as a measurement). **No shipped
  decision changed:** `low_risk` still `confirmed` in both split directions, `insider` still
  `rejected`. Full three-way A/B in `HANDOFF_edge_audit.md` Part 3.
- **R1 RE-RUN, DONE 2026-08-05 (audit session 4) — THE THRESHOLD IS CLEARED AGAIN ON THE
  CORRECTED PANEL, AT A LOWER LEVEL AND WITH A DIFFERENT MECHANISM. CLAIM A STILL APPLIES.**
  The pre-commitment in `HANDOFF_r1.md` section 1 was honoured unchanged ("alpha" only if the
  FF5+MOM intercept is positive with NW t > 2.0; ambiguous is a NULL). Re-run on the corrected
  69-date panel → **68 non-overlapping 63d windows, 2009-01-15 → 2025-10-27**, deployed flat
  1/7 weights, NW lag 1. Alignment check passes (SPY on MKT: beta 0.933, R² 0.988).
  * **FF5+MOM alpha +6.99%/yr, NW t +3.984, R² 0.308** on the primary object (`top − ew`).
    **ALL SIX pre-registered specs are positive with t > 2.0** — compound/sum × full/first
    half/second half, spanning **+5.08% to +10.85%**. No disagreement, so the pre-registered
    NULL veto is not triggered. **QUOTE +6.99%/yr (range +5.1% to +10.9%)**; the conservative
    single number is the first half's +5.19%.
  * **THE OLD +8.81%/yr AND THE +6.6%–8.8% RANGE ARE VOID. Do not quote them anywhere.**
  * **THE MECHANISM REVERSED ON TWO OF ITS THREE LEGS — this is the part to re-read.** Now
    loading: **HML +0.251 (t +2.93)** and **UMD +0.205 (t +3.65)**. NOT loading: **SMB +0.208
    (t +1.39)** and **RMW +0.092 (t +0.90)**, both of which loaded strongly in the void run
    (SMB t 3.84, RMW t 4.49). So the old story — "`size`, `quality`, `momentum` ARE the
    standard premia; `value` and `capital_discipline` are not what FF measures" — is
    **backwards on size and profitability** and must not be repeated. Current honest reading:
    momentum is a genuine standard-premium exposure, the book now carries a real VALUE tilt,
    and the size/profitability exposures that dominated the old story were largely an artefact
    of the inverted-universe window B6 removed. R² fell 0.465 → 0.308 — the factor models
    explain LESS of this series than of the void one.
  * The unhedged small-cap tilt caveat WEAKENS for the spread (SMB +0.208, t 1.39, vs +0.885
    before) but SURVIVES for the long-only book (SMB +0.691, t 3.89).
  * Other objects: long-only book in excess of RF **+9.33%/yr (t 4.97)**; long-short
    **+14.86%/yr (t 4.18)**; the equal-weight universe's own unexplained excess +2.34% (t 2.92).
  * **CAVEAT THAT MUST TRAVEL: the secondary q-factor model does NOT clear on the first half**
    (q4 +3.17%, t 1.712; q5 +1.56%, t 0.702), though it clears on the full sample (+6.72%,
    t 3.19) and the second half (+11.49%, t 3.84). The pre-registered threshold is stated on
    FF5+MOM so this does not veto, but the early-period result is model-dependent.
  * Against X7's floor: raw top-decile alpha +7.13% is far outside the placebo null
    [−1.33pp, +2.38pp], so R1 is decomposing something real. **X7 does NOT calibrate a
    factor-regression intercept** — no placebo floor exists for R1's own t, and none was
    invented. Still ONE panel; **X8's international replication is the out-of-sample evidence,
    R1 is not.** Full entry: `HANDOFF_edge_audit.md` Part 5.
- **SUPERSEDED 2026-08-05 by the R1 RE-RUN above. Every number in the next bullet was measured
  on the pre-B6/B7 panel over a window that no longer exists, with a composite no shipped code
  path uses. Kept only as the record of what was claimed. DO NOT QUOTE IT.**
- **SETTLED 2026-08-04 (audit R1) — THE HEADLINE IS NOT MERELY FACTOR EXPOSURE. The word
  "alpha" is now permitted, as a RANGE and with caveats.** `top_decile_alpha` is still
  `4 × (mean top-decile 63d return − mean equal-weighted universe 63d return)` with no risk
  adjustment in it, but that object has now been regressed on the factors it was suspected of
  merely re-assembling. On the full 2,710-name universe, 109 non-overlapping 63-trading-day
  windows (1998-12-31 → 2026-01-21), deployed flat 1/7 weights: **FF5+MOM alpha +8.81%/yr,
  Newey–West(1) t +5.742, R² 0.465**; Hou–Xue–Zhang **q4 +9.14% (t +5.23)**, q5 +8.33%
  (t +4.37); long-short **+12.12% (t +4.14)**. Raw was +12.13%, so **the factor models absorb
  about 27% of the headline and leave the rest** — the opposite of the pre-registered
  expectation. It passes all four pre-registered specs (compound/sum × full/ex-B6), every
  subperiod, every NW lag 0–8, **net of costs (+7.85%, t 5.16)**, and a spanning test adding the
  EW universe's own excess return (+8.25%, t 5.88; universe loading t 0.63, insignificant).
  **QUOTE THE RANGE +6.6% to +8.8%/yr** — +6.6% (t 4.41) is the value after dropping the 37
  B6-contaminated early dates, and is the right single number when only one is wanted.
  **Mechanism:** SMB +0.39 (t 3.84), RMW +0.30 (t 4.49), UMD +0.18 (t 3.49) all load — `size`,
  `quality`, `momentum` ARE the standard premia — but **HML (t 1.08) and CMA (t 1.08) do not**,
  so `value` (six ratios, EV re-priced at the rebalance date) and `capital_discipline`
  (issuance/accruals) are not what FF measures. Not a benchmark artifact: alpha is linear, so
  α(top−ew) = 14.60 − 5.80 = 8.81 exactly and the +5.80% (t 5.41) that FF5+MOM fails to explain
  about the EW universe itself **cancels out of the spread**. **CAVEATS THAT MUST TRAVEL WITH
  IT:** it is still ONE panel — a regression is a control, not new data, and **X8's international
  replication is the out-of-sample evidence, R1 is not**; **t 5.74 is NOT multiplicity-corrected**
  (audit M1 still open), though the deployed weights are flat 1/7 and were never tuned; FF5+MOM
  is a poor description of this universe so read loadings as approximate; the book carries an
  unhedged SMB +0.885 small-cap tilt with borrow/impact/capacity unmodelled; and the benchmark
  is still uninvestable (audit R10). Reconciles with X4 rather than contradicting it — over X4's
  own 2014+ window R1 gets +6.06% (t 3.16) where X4 got t 1.10, because X4 differences two
  high-variance total-return series (low power) while R1 removes that variance first (high
  power). Full write-up and the pre-commitment (written before any number) in `HANDOFF_r1.md`;
  reproduce with `python -m scripts.factor_alpha`, pinned by `tests/test_factor_alpha.py`.
- **R1 FRAGILITY (2026-08-04, same lane) — the result SURVIVED a deliberate attempt to break it,
  but it is WINDOW-DEPENDENT and has a WEAK DECADE, and it is PROVISIONAL until re-run.** Four
  criteria were committed before any cut ran; all four passed. **(1) Stable-universe window
  (≥2008, the closest available preview of what B6 will do): alpha +6.24%, t +3.986, n 73 —
  DOWN 2.57pp, about 29% of the alpha.** The discarded early period is where the raw spread is
  biggest (first third raw +21.89%/yr vs +3.53% and +11.02%), exactly the inverted-universe
  signature. **Expect the post-B6 headline near +6%, not +8.8% — quote ~+6% when one number is
  wanted.** (2) No sign flip: halves +8.98% (t 3.38) / +5.48% (t 3.12); thirds +13.51 (t 3.59) /
  **+4.33 (t 2.412, the weakest cell in the study)** / +8.10 (t 3.82). (3) **Not concentrated:**
  the best 5 of 109 periods carry 23.0% of the alpha (38.0% on the stable window, the criterion
  that came closest to tripping); dropping the best 5 leaves +7.28% (t 5.19), dropping the worst
  5 gives +10.07% — nearly symmetric, and the best 5 are spread across four regimes. (4) **Not
  specification-dependent:** CAPM +12.99%, FF3 +12.28%, FF5-no-MOM +10.03%, FF5+MOM +8.81%,
  q4 +9.14%, q5 +8.33% — all t > 2 on BOTH windows, and **FF5+MOM is nearly the most conservative
  of the six**, so the headline is quoted from the most demanding pre-registered model, not the
  most flattering. **THE ONE THING THAT LOOKS BAD: a ~10-year rolling window centred on 2009-2019
  shows alpha of only +1.66% (t 1.39).** Alpha is positive in 70 of 70 rolling windows and never
  reverses, but 8 of 70 are not significant — the full-sample t 5.742 averages a weak decade in
  with strong ones. Windows confirmed **genuinely non-overlapping** (all exactly 63 factor days,
  zero shared days), so no inference correction is needed. **BINDING: R1 MUST be re-run after B6
  and B7 land** — B6 is expected to lower alpha to +5.5-7.0%; B7's direction is unknown; a
  post-re-run alpha < +4%/yr or full-sample t ≤ 3.0 is a MATERIAL REVISION that requires
  rewriting the headline, and a stable-window t ≤ 2.0 withdraws the word "alpha" entirely. Full
  contract and every cut in `HANDOFF_r1.md` §6-8; reproduce with
  `python -m scripts.factor_alpha_fragility`, pinned by `tests/test_factor_alpha_fragility.py`.
- **Zeroing `insider` was tested the same way and REJECTED — it stays at 0.125.** It helped one
  split direction by a hair (Δt +0.08) and hurt the other (Δt −0.09). Its −0.34 full-sample
  t-stat is not a stable property. Same reasoning as `low_risk`, opposite outcome — which is
  why every theme change now has to clear `holdout_theme_validate()` before it ships.
- **CORRECTED — "the entire edge is the institutional (13F) theme" is OBSOLETE.** Strip the
  institutional theme now and top-decile alpha is still **+10.6%** with long-short t **2.86**
  (it used to collapse to 0.71). That finding was an artifact of `quality` and `low_risk`
  running on half their inputs. 13F is a contributor, not the whole edge.
- **CORRECTED — `monotonicity`'s SIGN WAS BEING READ BACKWARDS everywhere.** Deciles are
  ordered best-composite-first, so **−1.0 = perfectly ordered (ideal) and +1.0 = backwards.**
  The old bullet "monotonicity is negative at every lag (−0.68 at best) — the deciles aren't
  cleanly ordered" said the opposite of the truth: −0.68 meant they *were* well ordered.
  Current value −0.939. Pinned by `test_monotonicity_sign_convention`.
- **CORRECTED — `low_risk` does NOT have pooled IC −0.048.** With both its inputs finally
  populated it is **−0.0014 (t +0.71)** on the full universe: indistinguishable from zero.
  It was dead weight, not actively harmful. It is **−0.352 correlated with `size`** — the
  strongest anticorrelation in the theme matrix — so it was cancelling the small-cap tilt,
  which is why removing it helped so much despite having no signal of its own.
- **CORRECTED AGAIN 2026-08-07 (claims audit) — `institutional` coverage is 71.7%, and `insider`
  is 83.1%.** This bullet read "**`institutional` coverage is 61.4%**, not the 81.7% previously
  recorded". 61.4% was measured on the P6-era 110-date panel (that file reads 0.6140 in the same
  field); the current run reads **0.7172**. It rose for a mechanical reason worth knowing: B6
  dropped the 41 pre-2008 dates, and the theme is **empty before 2013-06-30**, so removing empty
  dates raises its coverage without adding any data. Same check on `insider`: **85.0% → 83.1%**
  (0.8504 → 0.8308). Any early-period comparison involving `institutional` is still uninformative
  rather than negative.
- **THEME ICs — CORRECTED 2026-08-06 (session 6, X3 re-run). THE TABLE THAT SAT HERE WAS A
  PRE-B6 MEASUREMENT MISLABELLED "CURRENT", AND `size` IS THE ENTRY THAT MOVED MOST.** It read
  "quality +3.57, momentum +2.62, capital_discipline +2.25, institutional +1.81, size +1.68,
  value +1.52, growth +1.45, low_risk +0.71, insider −0.43". **Proven stale, not inferred
  stale:** re-running `theme_ic` on the old 110-date panel reproduces that list to the digit
  (momentum +2.62, capital_discipline +2.25, institutional +1.81, size +1.68, growth +1.45,
  low_risk +0.71), so it was measured before the B6/B7/B13 corrections of 2026-08-04 and
  carried forward with a date that made it look newer than the panel it came from.

  | theme | void (110 dates) | **CORRECTED (69 dates)** | move |
  |---|---|---|---|
  | quality | +3.57 | **+3.10** | −0.47 |
  | capital_discipline | +2.25 | **+2.76** | **+0.51 — the only riser** |
  | institutional | +1.81 | **+1.55** | −0.26 |
  | momentum | +2.62 | **+1.31** | −1.31 |
  | value | +1.52 | **+0.84** | −0.68 |
  | growth | +1.45 | **+0.75** | −0.70 |
  | low_risk | +0.71 | **+0.46** | −0.25 |
  | insider | −0.43 | **−0.24** | +0.19 |
  | **size** | **+1.68** | **−0.30** | **−1.98** |

  **Against X7's calibrated bar of 2.71, TWO of nine themes clear: `quality` and
  `capital_discipline`.** Under the retired 2.0 convention the void table showed three, and
  X7 measured that 39% of pure-noise draws produce at least one theme at t ≥ 2.0. **`size` is
  now the WORST-ranked theme and the one whose removal costs the most** — see the X3 bullet
  below. sentiment still empty.
- **A FULL BACKTEST IS NOT REPRODUCIBLE RUN TO RUN, AND THE INSIDER THEME IS WHERE IT SHOWS.
  Found 2026-08-04; unexplained; do not build on any single run's insider number.** Three
  full-universe runs on identical data gave `insider` median IC **−0.00335 (t −0.34)**,
  **+0.01551 (t +2.69)** and **−0.00339 (t −0.43)** at unchanged 85.0% coverage. The first and
  third bracket the second and agree to four decimals, so the middle run is the anomaly and
  **audit B26 (the same-day-filing exclusion) is NOT the cause** — an earlier note in this file
  said it was, and that was wrong. B26's effect was measured directly on 22,975 (ticker, date)
  score pairs: it alters **3.96% of scores at a level correlation of 0.9975**, consistent with
  the ~0 IC change between the runs that bracket it. Every other theme is stable to ±0.01 across
  all three runs. **What this means: `insider`'s IC sits so close to zero that its t-statistic is
  not a measurable quantity**, which is exactly why zeroing it came back `not_replicated`
  (Δt +0.08 one direction, −0.09 the other). It is also a reproducibility problem in its own
  right — a project whose memory is its results files needs its results files to be
  deterministic. **Next session: find the nondeterminism before trusting any marginal IC.**
  Audit item **S3** (the `+min(10, 2·buys)` bonus is unconditionally additive; `tanh(net/5e6)`
  saturates regardless of company size) is the thread that might make this theme measurable.
- **Historical note:** `insider` is the only negative theme, and still carries 12.5% weight — but
  zeroing it **did NOT replicate** out-of-sample, so it was deliberately left alone.
- **Theme ICs are NOT stable across time.** `low_risk` flips −0.031 → +0.041 between halves and
  `size` flips t +3.17 → −0.67 (the small-cap premium worked pre-2012, not after). Treat any
  single-period theme IC as weak evidence; the held-out split is what settles a decision.
- **13F is NOT a look-ahead artifact (settled July 2026, 800 names).** Feeding it *fresher,
  not-yet-filed* data at a 15d lag makes it WEAKER, not stronger (t 1.49 -> 0.66, Deflated
  Sharpe 84% -> 44%) — the opposite of the artifact signature. The panel's effective lag is
  already ~111 days (an April rebalance uses the December quarter, public since mid-February),
  i.e. more conservative than the 45d deadline. Its decay curve is sensible: peaks at Q-1,
  alive at Q-2 (t 1.36), dead by Q-3 (t -0.04).
- Edge is strongest in **large caps** (regime IC highest there).
- **P6: THE EDGE SURVIVES TRADING COSTS — BUT ITS COST PROFILE IS STALE. CORRECTED 2026-08-07
  (claims audit).** It read: *"Top-decile breakeven is **236 bps one-way** against a
  **37 bps** actual cost profile (~6.4x margin); net alpha **+11.41%/yr** after costs on 249%
  annual turnover."* On the corrected 69-date panel the `costs` block reads **breakeven 134.1 bps
  one-way against a measured 33.4 bps (4.0x margin), net top-decile alpha +6.07%/yr on 261%
  annual turnover.** (The corrected-panel bullet above already fixed breakeven and the "37 bps was
  an assumption, not a measurement" point (B11); the net alpha and turnover here were never
  updated.) **The conclusion is unchanged — a 4.0x margin still clears comfortably.** The
  bottom-decile figures in the next sentence are P6-era and were NOT re-measured by the claims
  audit — treat them as unverified, not as corrected. The short
  side does not break it either — the BOTTOM decile is *larger*-cap
  than the top ($4.50B vs $1.95B median, 29.8 vs 37 bps), so the long-short t does not rest on
  unborrowable micro-caps. Borrow cost is not modelled (affects the long-short statistic, not
  the long-only book). Quote the BREAKEVEN, not the net alpha — it needs no belief in any
  particular cost calibration. Measured on every run now (`costs` block).
- **P6: three plausible refinements were tested and ALL THREE REJECTED.** Do not re-open them
  without a new reason: **(a) TTM ROE/ROIC is WORSE than quarterly** (roe t +2.84 vs +2.01,
  roic +3.38 vs +2.57) — recency beats smoothing, and the earlier note calling quarterly a
  "wart" was wrong; **(b) median/MAD robust z-scores HALVE the long-short t** (3.485 -> 1.721);
  **(c) consolidating momentum+institutional loses** (LS t 3.48 -> 2.53) — +0.50 correlated but
  complementary, both earn a full weight.
- **P6 lesson worth keeping: a signal's IC can be flat while the composite built from it moves
  a lot.** Robust z-scores left every theme IC essentially unchanged (quality +3.39 -> +3.35)
  while halving the long-short t. Rank-IC is INVARIANT to a monotone rescaling; the composite
  is a weighted SUM of z-scores and is very much scale-sensitive. **Never judge a
  standardization or scaling change by per-signal IC.**
- **CORRECTED — `sector_neutral` WAS silently inert; it is now wired, TESTED, and REJECTED.**
  The old text ("no sector column anywhere on disk ... BLOCKED until TICKERS is downloaded") is
  obsolete: TICKERS was downloaded in P10 and the panel populates `metrics["sector"]` from it.
  Sector coverage is **100.0% of panel rows** (2,710/2,710 names, 11 sectors), so the toggle
  genuinely changes every z-scored theme instead of grouping on a constant. It was then measured
  on the full universe and **rejected in both held-out directions, twice** (P10, and an
  independent re-run 2026-08-02 on a panel that had since gained several signals). Under the
  DEPLOYED weights it raises long-short t 3.396 → 3.896 but COSTS top-decile alpha
  +11.82% → +10.24%, worsens monotonicity −0.952 → −0.915 and nearly doubles PBO 26.7% → 46.7%;
  the later half is worse on both metrics. `sector_neutral` stays **OFF**. Full numbers in
  `HANDOFF_sector_neutral.md`; wiring pinned by `tests/test_sector_neutral.py` so it cannot
  silently go inert again. TICKERS gives TODAY's classification, so applying it to 1998 rows is
  a mild look-ahead — the one non-point-in-time input in the panel, which is a reason to be MORE
  sceptical of a positive sector result, not less. It rejected anyway, so nothing rests on it.
- **P7: THE VALUE THEME WAS CURRENCY-CORRUPTED and is now fixed.** `marketcap`/`ev` are USD but
  the raw line items are in the REPORTING currency, so every value ratio was wrong for the 4.1%
  of rows that report abroad — SK Telecom's `book_to_price` computed to **892 vs a true 0.589**.
  All six value inputs improved after the fix (**value theme t +1.34 → +1.46**), **PBO halved
  13.3% → 6.7%**, monotonicity −0.939 → −0.952, top-decile alpha +11.77% → +11.82%. Foreign
  over-representation in the top decile went **1.35x → 0.56x**; in the live book, foreign names
  fell from 21 of 86 positions (28.3% of weight) to 11 (10.7%).
- **`fxusd` IS A DIVISOR, NOT A MULTIPLIER** — local units per USD (SKM 1514.2 won/USD). Using
  it as a multiplier squares the error. There is **no `netincusd`** column; use `netinccmnusd`.
  `total_equity` must stay LOCAL — `gp_on_capital` divides local gross profit by it.
- **ENTERPRISE VALUE IS NOW PRICED AT THE REBALANCE DATE (2026-08-03, shipped ON).** Sharadar's
  `ev` embeds the FILING-date market cap, so `ebit_ev`/`ev_sales`/`ev_ebitda` measured cheapness
  against a ~111-day-old quote while `earnings_yield`/`fcf_yield`/`book_to_price` used the fresh
  one. `_pit_ev()` re-prices the EQUITY leg to the PIT market cap and holds the DEBT leg at its
  last filed value (net debt is only observable at a filing — that IS point-in-time). Net debt
  must be **currency-converted before it is added** — P7 in a second costume. Re-pricing moves EV
  a **median 5.1%** (26.7% of rows >10%), and `neg_ev_sales` median IC goes **+0.0214 → +0.0363**.
  The BOOK is a wash (LS t 3.396 → 3.520, alpha +11.82% → +11.88%, PBO/monotonicity unchanged,
  net top-decile alpha slightly worse) — **it ships on correctness, not performance.** Stale, not
  look-ahead, so no past result is invalidated upward. New **`ev_freshness`** block (100.0% fresh)
  makes a silent revert loud; `EDGE_EV_POINT_IN_TIME=false` reverts. `HANDOFF_ev_fix.md`.
  STILL OPEN: negative EV (net cash > market cap, 0.70% of rows) is read as maximally cheap by
  `neg_ev_sales` and as expensive by `ebit_ev` — a live sign inconsistency, deliberately not
  bundled into this change.
- **P8: a SANITY layer now runs every backtest** (`sanity_check` block): range / subgroup-pegging
  / market-cap divergence. Coverage says a factor is PRESENT, this says it is SANE — the
  currency bug filled every column and coverage was blind to it. Verified it WOULD have caught
  P7 (foreign names sat at the 86th percentile of book_to_price and earnings_yield pre-fix).
  It legitimately fires twice on corrected data (foreign names really are large caps; 1.45% of
  rows have a >3x market-cap divergence, AIV 71x / EQC 53x). **Do not silence a flag to make the
  run green** — investigate it or record why it is expected.
- **CODE_AUDIT.md's M2 (SanDisk/WDC ~10x) does NOT reproduce.** DAILY cap and shares x price
  agree to 1.6x, the share count is plausible, and the price ran 29.6x over 17 months with zero
  discontinuities (WDC 10.3x, MU 8.5x — the whole storage complex). If it is wrong the error is
  upstream in the PRICE, which both estimates share. Unresolved, not fixed.
- **Standing caveats, do not drop them — TWO OF THEM WERE RETIRED BY MEASUREMENT AND ARE
  CORRECTED HERE 2026-08-07 (claims audit). This bullet says "do not drop them", so both wrong
  caveats were being propagated on purpose; that is why they are corrected rather than deleted.**
  * **The Deflated Sharpe caveat WAS WRONG.** It read: *"Deflated Sharpe is a saturated
    0.9999991 and, per the B9 correction at the top of this section, it is an **undeflated PSR**
    — not a proof of anything."* Both halves are void since M1 (2026-08-05): the shipped run is
    **0.8997 at N = 84 and 0.8674 at the current N = 116** — not saturated — and it self-reports
    `metric = deflated_sharpe_ratio` with `is_effectively_undeflated = false` (`sr0` 0.406
    against a per-period Sharpe of 0.550). **The live caveat is the opposite one:** it is a
    genuine Deflated Sharpe that **FAILS** the >0.95 convention while sitting above all 100
    placebo draws (X7 floor 0.72). Quote it whole, per the M1 bullet.
  * **The B8 caveat is STALE.** It read: *"the test is a **both-halves stability check rather
    than an out-of-sample confirmation** (B8)"*. B8 was fixed in session 7: `oos_verdicts` now
    enforces the documented rule alongside the frozen `stability_verdicts`, and `low_risk` reads
    `confirmed_oos`. The surviving caveat is narrower and is stated in the B8 bullet above —
    **`low_risk` is confirmed out-of-sample in ONE of two split directions, not two.**
  * Still true, unchanged: both halves come from the same panel and universe, and the
    size-cancellation mechanism was hypothesised on the full sample — so neither the decision nor
    the hypothesis generation is out-of-sample in the strict sense. The concentrated top-25 book
    is the noisiest number in the file, and per audit **B17** it holds up to FIFTY names (it sells
    only below `exit_rank = top_n × 2`) and pays neither costs nor taxes, unlike every other book
    in the results file — so it is also mislabelled. Weight-tuning itself remains noise-chasing:
    CPCV still adopts no weighting over the defaults. (All three re-verified 2026-08-07:
    `exit_rank = top_n * 2` at `fundamental_panel.py:1710`, which also ships a `label_warning`
    saying the realised book size is ~`exit_rank`, not `top_n`; `cpcv.adopt = false`.)
- **FIXED 2026-08-04 (audit session 2). The panel is now a genuine 18.5-year window,
  2008-01-16 → 2026-07-24, 69 rebalance dates, cross-sections 1,471–1,954.** `days=None` means
  the whole series and the shared calendar is cut ONCE, before the ffill. Each run ships
  `panel_window` (available vs retained range, the cut, per-date cross-section sizes) so the
  two-blocks-disagree-about-their-window failure cannot recur silently. **41 of the 110 dates
  were dropped and the headline fell with them — see the CORRECTED PANEL bullet above; this was
  the most expensive correction in the audit.** The description below is what the defect WAS:
- **The panel is 27 YEARS long, not 18, and its first third has an INVERTED universe (audit
  B6, FIXED — see above).** `WRDSProvider.price_history` truncates with `.tail(4659)`, so each
  ticker keeps its OWN last 18.5 years and the calendar is the union: 1998-12-31 → 2026-04-22,
  110 rebalance dates over 27.3 years. At a 2001 cross-section every name present is one that
  stopped trading by roughly 2019 — the inverse of classic survivorship bias, and it makes
  roughly the first 37 of 110 periods uninterpretable. Those same 37 dates have no benchmark,
  which is why `construction.n_periods` reads 110 while `portfolio.n_periods` reads 73 in the
  same JSON over undisclosed windows. Direction of the bias is genuinely unclear.
- **FIXED 2026-08-04 (audit session 2, B7/G). There is now ONE composite**, used by selection,
  measurement and live, and it renormalises by the present-weight mass — the convention
  SELECTION already used, so the deployed weights were chosen under it. `CONFIG.sector_neutral`
  and `CONFIG.residual_momentum` now default **false**. **Live and backtest score identically**
  (max abs difference 0.0), pinned by
  `test_audit_b7_the_live_path_and_the_backtest_path_score_identically`. Measured effect on the
  headline: **NULL** (t −0.010, alpha +0.01pp) — the disagreement was real in mechanism but
  small in magnitude on this panel. The description below is what the defect WAS:
- **The LIVE product does not score names the way the backtest does (audit B7/G, FIXED — see
  above).** `screen.py:256` (now **`screen.py:232`**, re-resolved 2026-08-07) calls
  `build_frame(metrics)` with no keyword arguments — it still does, which is now CORRECT because
  the CONFIG defaults are false; at the time it inherited
  `CONFIG.sector_neutral` (default **true**) and `CONFIG.residual_momentum` (default **true**),
  while the backtest forces both `False`. Sector-neutral ranking was tested on the full universe
  and rejected in both held-out directions, twice. **Unless `SCREENER_SECTOR_NEUTRAL=false` is
  set in the environment, the hot list users see is scored under the intervention the research
  eliminated.** There are also three different composite functions in the tree (selection
  renormalises by present-weight mass, measurement does not, live renormalises AND adds the two
  interventions), so **no shipped code path reproduces the backtested composite exactly.**

**HISTORICAL — P5 era, 2026-07-30. DO NOT READ THIS FIRST; MOST OF IT IS SUPERSEDED BY THE
BULLETS ABOVE.** **CORRECTED 2026-08-07 (claims audit): this header used to read "LATEST
(2026-07-30) — SUPERSEDES much of CURRENT STATE above. Read this first." That was true when
written and is now backwards** — `CURRENT STATE` above carries material through 2026-08-06, so
the old instruction sent a cold reader to the OLDEST numbers in the file and told them they
superseded the newest. In particular the "CLEARS both bars for the first time" bullet below
(PBO 13.3%, Deflated Sharpe ~100%, long-short t 3.485, top-decile alpha +11.77%) is **void** —
it was measured on the pre-B6 110-date panel. The live numbers are t 2.836 / alpha +7.17% /
PBO 73.3% / DS 0.8674. The three era headers read newest-to-oldest: **CURRENT STATE (through
2026-08-06) → this section (2026-07-30) → PREVIOUS (2026-07-29).**
- **Five wired factors were SILENTLY EMPTY in every run this project has ever done.** The
  Sharadar export is ARQ-only and Sharadar fills its ratio/averaged columns only in ART/ARY:
  `roe`, `roic`, `assetturnover` are non-null in **0 of 197,265 rows**. `beta` was hard-coded
  `None`. `growth_accel` was overwritten with all-NaN by `build_frame`. So `quality` averaged
  **8 of its 10** inputs, `low_risk` **1 of 2**, `growth` **1 of 2** — with no error, ever.
  All four are now derived from line items that were present all along. `_f()` also returned
  NaN instead of None, which made `_f_score` count MISSING tests as FAILED ones.
- **A coverage guard now exists and would have caught every one of them**: `signal_coverage()`
  warns on any wired signal under 5% coverage and ships a `signal_coverage` block in
  BACKTEST_RESULTS.json. **Never trust a factor's IC without checking its coverage first.**
- **roic (t +3.38) and roe (t +2.84) are the 4th and 6th strongest signals in the panel** and
  were contributing nothing. `quality` is now the strongest theme (t +3.39).
- **`monotonicity`'s SIGN HAS BEEN READ BACKWARDS throughout these notes.** Buckets are
  ordered best-composite-first, so **−1.0 = perfectly ordered (ideal), +1.0 = backwards.**
  The "monotonicity is negative ... the deciles aren't cleanly ordered" line above is WRONG,
  and P4's "−0.782 → −0.855, slightly worse" was an improvement. Now pinned by a test.
- **`low_risk` zeroed (live, reversible).** Its real full-universe IC is −0.0014 (t +0.71),
  NOT the −0.048 claimed below — dead weight, not harmful. It is **−0.352 correlated with
  `size`**, the strongest anticorrelation in the theme matrix: low-beta/low-vol names ARE
  large caps, so it was cancelling the small-cap tilt. `neg_asset_growth` also dropped
  (t −0.70, wrong sign).
- **The full-universe verdict CLEARS both bars for the first time: PBO 13.3%, Deflated Sharpe
  ~100% (saturated), long-short t 3.485, top-decile alpha +11.77%.** BUT the biggest
  contributor (zeroing low_risk) was chosen by looking at this same panel, so it is
  **in-sample-informed and needs out-of-sample confirmation** — HANDOFF_STATUS.md §5.
- **"The entire edge is 13F" is now OBSOLETE.** Without the institutional theme, top-decile
  alpha is still +10.6% and long-short t 2.86 (was 0.71). That finding was an artifact of
  quality/low_risk running on half their inputs.
- **`insider` is the only negative theme (t −0.34, now −0.43) and still carries 12.5% weight** —
  the obvious next candidate, deliberately NOT changed. **See the reproducibility note above:
  one of three identical-data runs returned +2.69, so this theme's t is not a measurable
  quantity in either direction. The held-out verdict is `rejected` in all three runs.**
- Real full-universe coverage: `institutional` **61.4%** (not the 81.7% below), `insider`
  85.0%. F-Score is **t +2.74** on the full universe, not +5.66.

**PREVIOUS (2026-07-29) — several claims below are corrected above:**
- **800-name large-cap run:** PBO 13%, Deflated Sharpe 77%, first CPCV "adopt" (`ic-ir`), top-decile
  +4.1%/yr vs equal-weight. BUT it's the friendlier large-cap universe (not the fair 3,000), still
  <95%, still ~1/3 13F-dependent. **The full 2,827-name run has STILL never completed** (scoring loop slow).
- **F-Score is the strongest new signal** (IC t +5.66), wired into quality; accruals + 13F-holder-breadth
  also kept. Classic anomalies (reversal, idio-vol, MAX, low-vol) did NOT replicate here.
- **`low_risk` theme has NEGATIVE pooled IC (-0.048)** and CPCV zeroed it — a live factor that's hurting;
  not yet changed (Don's call).
- **`assets` was silently dropped by the loader**, so `capital_discipline` was half-empty in every prior
  run — fixed; treat past capital_discipline conclusions as unreliable.
- **Bulk data loaded fast+safe** via `valuation/edge/bulk.py` (raw zips in `data/raw/`, extracts in
  `data/bulk/`, caches in `data/bulk/prepared/`): SF3 per-manager conviction, DAILY point-in-time
  marketcap+ratios, ACTIONS splits/delistings, EVENTS raw codes.
- **THE SCHEMA LEGENDS ARE IN `SHARADAR_REFERENCE.md` (`47cb189`, 2026-08-03) — CHECK IT BEFORE
  CONCLUDING A CODE IS UNLABELLED.** It transcribes what the bulk downloads do NOT carry and the
  API does: the full **`EVENTCODES` (37)** and **`ACTIONTYPES` (19)** legends, per-column
  `unittype` for all 112 SF1 fields, and a **first/last-seen date per event code** — which is how
  `SC-2` found that codes 34 and 35 stop in 2024-12/2025-05. `CLAUDE.md` cited this file **zero
  times** until now, which is why `S17` closed on 2026-08-13 recording that the legend did not
  exist while it had been in-tree for ten days.
- **Now CONSUMED by the panel (2026-07-29 s3):** point-in-time market cap from DAILY (replaces the buggy
  shares×price path; AAPL 2015Q2 $722.6B verified), survivorship-free returns via the ACTIONS delisting
  mask (SEP is ALREADY split-adjusted, so split ratios deliberately NOT re-applied — don't "fix" that),
  SF3 conviction exposed as inputs (`sm_conviction/holders/breadth`, not yet in a theme). `institutional`
  coverage 70.5%→81.7%. STILL PENDING: scoring loop unvectorized; **full 2,827-name run has never completed.**

## METHODOLOGY RULE (hard — do not violate)
**CORRECTED 2026-08-07 (claims audit): THE FULL UNIVERSE IS ~2,531 NAMES, NOT ~2,710. This rule
used to name 2,710 and an agent seeing 2,531 could reasonably think it was looking at a subset
and withhold a verdict.** 2,710 was the P6-era 110-date panel (`git show b0f70b6:BACKTEST_RESULTS.json`
= 2,710 names / 110 dates); every run since the B6/B13 corrections of 2026-08-04 reads
**`universe.n_names` 2,531, `n_dates` 69, `label` "full"**. The rule itself is unchanged and the
code enforces it: `WRDSProvider.universe` returns the whole export when `limit` is None or >= its
size, and prints a "SMOKE-TEST SUBSET, not a verdict" banner otherwise (`data_providers.py:388-409`).
Read "~2,710" as "~2,531" wherever it still appears below.

**Report verdicts ONLY from the full ~2,531-name universe.** 400/800-name subsets systematically
flatter results (PBO 13% on 800 → 53% on full; `sm_breadth` t 2.37 on 800 is unverified on full).
**CORRECTED 2026-08-03 (audit B12): the 800-name era was an ALPHABETICAL slice, not the 800
largest.** `WRDSProvider.universe` returned `sorted(keys)[:limit]`, so those runs were names
beginning with roughly A through C. "PBO 13% on 800 → 53% on full" was therefore never measuring
how much a large-cap tier flatters results — it was measuring how much an ARBITRARY 30%
alphabetical subsample does. The function is fixed (ranked by market cap, sort key printed in the
banner, subsets labelled smoke tests), but **every 800-name-era figure needs a full-universe
re-run before it is cited again**: the first CPCV "adopt", PBO 13%, Deflated Sharpe 77%,
`f_score` t +5.66, `sm_breadth` t 2.37, the 13F look-ahead stress test, and the four
classic-anomaly rejections (short-term reversal, idio-vol, MAX, low-vol).
Small samples are dev smoke-tests only ("does it compute / not crash") and MUST be labeled as such —
never the number a keep/reject/adopt decision rests on. The full run is now fast (~75s load + ~11s
score), so there is no performance excuse to judge on a subset. If you must screen small first, say
"smoke test" explicitly and re-run the survivor on the full universe before reporting a verdict.

## WHERE DO WE STAND? → **`VALQUO_LEDGER.md`**

**THE TASK LIST WAS DELETED HERE 2026-08-15 (master audit MA22), AND IT ASKED FOR THIS ITSELF.**
Its own header read: *"This list is the least trustworthy section in the file. Of the three OPEN
items checked against the tree on 2026-08-07, TWO were already closed"* — one had been rejected
with numbers four days before it was listed as "clearly worthwhile now", another was already
shipped, and a third was routed to the wrong lane for work that had been done in this repo.

**`VALQUO_LEDGER.md` is the contractual answer to "is X done?"** — one row per item, with verdict,
commit and handoff. It is 275 rows and it is maintained; the list here was neither.

**NOTHING WAS LOST, AND THAT WAS CHECKED ROW BY ROW BEFORE DELETING RATHER THAN ASSUMED.** Every
item carried here is recorded elsewhere, in every case more fully:
- the gated auto-apply of learned weights → ledger **`MA1`** (DISARMED, with the production
  verification and both commits — the task-list entry had none of that);
- estimate revisions → ledger **`D6`** (*"STAY PARKED. No retail point-in-time revisions exist at
  any price. Path is IBES via WRDS"*);
- sector-neutral ranking, PEAD, the ML tree combiner, the forward paper track → their own bullets
  in CURRENT STATE above, with the numbers;
- the monotonicity sign convention → pinned by `test_monotonicity_sign_convention`.

**The one standing instruction worth carrying forward:** `monotonicity` is ordered
best-composite-first, so **−1.0 is perfectly ordered and +1.0 is backwards**. Any pre-2026-07-30
conclusion quoting it should be re-read with the sign flipped.


## COVERAGE RULE (hard — learned the expensive way 2026-07-30)
**Before reporting or acting on any factor's IC, check its coverage.** Five wired factors were empty
for this project's entire history and nothing surfaced it: an empty column contributes nothing to a
theme mean, raises no error, and the run completes normally. `signal_coverage()` now warns under 5%
and writes `signal_coverage.below_floor` into BACKTEST_RESULTS.json — **read that block first.**
The same class of bug has now bitten four times (`assets` in the loader allowlist, the SF3
positional-arg bug, these five, and `invcap`/`taxexp`/`ebt` missing from `_KEEP`). When adding any
signal, add its source columns to `WRDSProvider._KEEP` and confirm coverage in the next run.

## Session close-out, tool routing, working with Don → **`RUN_RULES.md` PART 0**

**MOVED 2026-08-15 (master audit MA22).** The end-of-session handoff rules, the Claude-Code vs
Cowork routing, and the git handoff now live in `RUN_RULES.md` PART 0 alongside the other
operating instructions, so they are read at the start of a session rather than found 4,000 lines
into a findings record.

One correction was applied on the way, and it is the reason the move matters: the git-handoff
text said the Action *"runs all 24 suites"* while this file's own opening said **62** — measured
on the day of the move, **83**. It also cited `RUN_RULES.md:76`, a line number that had already
drifted. PART 0 derives the count and cites sections rather than line numbers.
