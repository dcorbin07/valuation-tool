# DECISION — making the corrected universe canonical

**STATUS: DECIDED BY DON ON 2026-10-07 AND RECORDED HERE BEFORE ANY FILE MOVES.** This memo is
the thing that lands first, so the move is executed against a written specification rather than
improvised. It is a plan and a contract, not a measurement: **no figure in it is new**, and every
number is read from an artifact this lane has already landed.

---

## 1. WHAT "CANONICAL" MEANS, AND THE ONE THING THAT MAKES THIS NOT A RENAME

Today the project's canonical object is the **2,531-name / 69-date** panel
(`panel_corrected_69d.pkl`), and `BACKTEST_RESULTS.json` is the file every public surface and
every successor reads. Making the corrected universe canonical means:

1. the **corrected 9,645-name panel** becomes the object the canonical run is built from;
2. `BACKTEST_RESULTS.json` is **re-run from a clean tree** against it;
3. the **corrected placebo draws** become the floors the pages read, replacing X7's;
4. **`INDEX_BOOK` is re-measured** on it;
5. every landed figure is **re-derived or marked `UNMEASURED`** — never carried forward silently.

**AND THE ONE THING THAT MAKES IT A CONSTRUCTION DECISION RATHER THAN A FILE SWAP: ON THIS
UNIVERSE CPCV ADOPTS FOR THE FIRST TIME IN THE PROJECT'S HISTORY.** `CORRECTED-FLOORS` part 1b
measured it: `placebo.py` and `run_backtests` both let CPCV decide, and on the corrected universe
it **adopts `ic-proportional`**. So a naive re-run would make the canonical headline describe the
**adopted** book — **top-decile alpha 2.83%** — while the book Don actually runs is the
**deployed flat 1/7** at **6.07%**.

**DON'S RULING, VERBATIM: the canonical run's HEADLINE must describe the DEPLOYED flat 1/7 book,
with the adopted book beside it under its own named block.** *"A canonical file whose headline is a
book nobody runs is the defect, whichever way it flatters."* Here it flatters **downward** — the
adopted figure is less than half the deployed one — and the rule is indifferent to that, which is
the point of stating it as a rule.

---

## 2. THE WORK, IN ORDER, WITH ITS GATE

| # | step | gate before it counts |
|---|---|---|
| 1 | `run_backtests` reports the **deployed** book as the headline and the **adopted** book in its own block | an AST test that the headline path never consults CPCV, plus a positive control that the adopted block is still populated |
| 2 | re-run `BACKTEST_RESULTS.json` **from a clean tree** | `errors: []`, `SCHEMA_VERSION` unchanged or additively bumped, and a leaf diff against the current file with every move attributable |
| 3 | the **corrected floors** become what the pages read | `CORRECTED_FLOORS.json`'s seven, by import rather than retyping; X7's seven stay on the record as the 2,531-name panel's |
| 4 | re-measure `INDEX_BOOK` | `served_index_book`'s `C1` keeps EXACT reproduction, re-targeted at the corrected panel's own deployed alpha (part 1b's instrument), never weakened |
| 5 | every landed figure re-derived or `UNMEASURED` | the three-state vocabulary, with an `UNMEASURED` row required to name its reason |
| 6 | hand the app fixer the old → new table in §4 | one table, every figure, with the file and symbol each lives in |

**THE HEADLINE CHANGE IS STEP 1 AND IT IS THE ONLY ONE THAT TOUCHES BEHAVIOUR.** Steps 2-6 are
measurement and reporting. If step 1 cannot be made to pass its gate, **the move stops there** —
a canonical file whose headline silently changed book is worse than no move.

---

## 3. WHAT MUST NOT MOVE, AND WHY EACH

* **`PAPER_TRACK_CONTRACT.md`'s frozen meter parameters** — σ 3.9847 pp/month, ρ = 3, α = 0.05,
  the cost drag, and the SUPPORTED/UNSUPPORTED bars. The contract's own §3 voids the **whole run**
  if a threshold changes, and §6 rule 6 says **σ may never be revised downward** (at 1.5× the
  assumed volatility the false-crossing rate is 20%). A universe change is not a reason to touch
  a pre-registered forward test.
* **The forward record** — `data/valquo_track_history.csv` and the bound series. **No backfill**
  (`DECISIONS.md`), and a vintage is a statement about a model as operated, not about a panel.
* **The deployed weights** — flat 1/7. This move changes which panel the canonical file measures,
  **not what the live book holds.** Changing the weights would be a vintage event and Don's
  separate call.
* **X7's seven floors as a RECORD.** They are correct for the 2,531-name panel and stay on the
  page labelled as such. The corrected seven do not *replace* them; they *supersede them for the
  corrected object*, which is a different sentence.

---

## 4. THE OLD → NEW TABLE FOR THE APP FIXER

Every public figure this move changes, where it lives, and its state in the three-state
vocabulary. **`SURVIVES` means the printed sentence is still true; `NO LONGER HOLDS` means it
needs restating; `UNMEASURED` means the move cannot settle it.**

### 4a. `valuation/web/hold_horizon.py` — the holding-horizon copy

| symbol | old | new | state |
|---|---|---|---|
| `ALPHA_ANN_FIRST_QUARTER` | **6.6** | **6.07** | **SURVIVES** — inside the declared 1.0pp |
| `ALPHA_ANN_TWO_YEARS` | **5.1** | **2.56** | **NO LONGER HOLDS** — a 2.54pp move |
| `RANK_IC_FIRST_QUARTER` | 0.0336 | **0.0594** | restate |
| `RANK_IC_TWO_YEARS` | 0.0655 | **0.1017** | restate; the claim *"rank IC rises with horizon"* **SURVIVES**, and more steeply |
| `PANEL_NAMES` | 2531 | **9645** | **NO LONGER HOLDS** — the surface names the panel every figure on it comes from |
| `PANEL_DATES` | 69 | 69 | unchanged |

**AND THE SHAPE CLAIM CHANGES, WHICH IS THE ONE A READER WILL MISS.** `S22`'s verdict moves
**CONSTANT-RATE → INTERMEDIATE**: `R_8` falls **6.195 → 3.3723** against S22's own 6.0 bar, and
annualised alpha **decays 6.07% → 2.56%** across the eight horizons where the published figures
were essentially flat. **The defensible sentence's second clause — *"still ahead by about 5.1%
annualized two years later"* — is the part that fails.** The persistence weakens; it is not
absent (the two-year HAC *t* is still **3.3845**).

### 4b. `valuation/web/score_confidence.py` — the hot-score confidence copy

| symbol | old | new | state |
|---|---|---|---|
| `PER_NAME_DATES` | **(45, 69)** | **(12, 69)** | **NO LONGER HOLDS** — below the register's own gate of 42 |
| `GROUP_DATES` | **(21, 69)** | **(57, 69)** | **NO LONGER HOLDS** — the disclaimer becomes a majority |

**BOTH MOVE IN THE PRODUCT'S FAVOUR, AND THE CAVEAT MUST TRAVEL WITH THEM.** The per-name verdict
*"not distinguishable from chance"* now holds on only 12 of 69 dates, i.e. individual names **are**
distinguishable on 57; and the group advantage is now a majority property rather than a recent
one. **But a 9,645-name cross-section makes a top decile of ~960 names rather than ~184, so a less
noisy group mean is PARTLY ARITHMETIC RATHER THAN INFORMATION** — and the producer's own
independence warning applies to both counts: *"69 overlapping cross-sections of largely the same
names are not 69 independent draws."* **Do not restate these as a stronger product claim without
that sentence attached.**

### 4c. The Index tab's backtested column (`INDEX_BOOK`, Roth)

| figure | published | corrected | of which newer data | of which wider universe |
|---|---|---|---|---|
| net annual return | **+17.162%** | **+18.017%** | **+1.2536pp** | **−0.3986pp** |
| max drawdown | **−23.029%** | **−28.959%** | **−4.2656pp** | **−1.6645pp** |
| Sharpe | 1.0318 | **0.9694** | −0.0543 | −0.0081 |
| alpha vs SPY | +1.949% | **+2.218%** | +0.666pp | −0.397pp |
| alpha vs equal weight | −0.058% | **+5.929%** | +0.675pp | **+5.312pp** |

**THE RETURN IMPROVEMENT IS ENTIRELY THE NEWER DATA AND THE WIDER UNIVERSE SLIGHTLY COSTS**, and
~72% of the drawdown worsening is newer data. **The alpha-vs-equal-weight jump is a BENCHMARK
EFFECT, NOT A BOOK EFFECT**: adding 6,600 smaller names drops the equal-weight benchmark from
17.8% to 12.1%, which is +5.31pp of the +5.93pp. **Quoting that line as the book improving would
be wrong.** The identity `(newer data) + (wider universe) = total` holds on every additive figure
at 1e-12.

### 4d. The research floors every page gates on

| floor | X7 (2,531 names) | corrected (9,645) | direction |
|---|---|---|---|
| max theme IC *t* | 2.7072 | **2.8852** | **HARDER** |
| long-short *t* (naive) | 2.0702 | **1.5102** | easier |
| long-short *t* (HAC) | 2.0567 | **1.4852** | easier |
| top-decile alpha margin | 0.018629 | **0.009738** | easier |
| top-decile alpha HAC *t* | 1.8262 | **1.6425** | easier |
| PBO (p5) | 0.19667 | **0.13333** | **HARDER** |
| Deflated Sharpe | 0.66366 | **0.59124** | easier |

**TWO OF THE SEVEN GET HARDER AND FIVE EASIER, so this is not a blanket loosening** — and a
figure must be compared against the floor calibrated **on its own object**. Pairing a corrected
statistic with an X7 floor, or the reverse, is the error `MA19` found in the record's own
*"0.8674 vs the 0.7216 floor"* (an `N` = 116 numerator against an `N` = 84 denominator).

### 4e. R1's factor-model intercept

| figure | old | new | state |
|---|---|---|---|
| FF5+MOM intercept | +5.94%/yr claimed on the corrected panel | **+5.9398%/yr at NW *t* 4.4532** | **SURVIVES** |
| net of cost | +7.85%/yr (t 5.16), **VOID pre-B6 panel** | **UNMEASURED by R1's own path** | see below |
| breakeven one-way | — | **123.46 bps**, ~3.7× B11's measured 33.4 | new, and the primary |

R1's own `net_of_cost` is `NaN` on this universe for a diagnosed reason: `factor_alpha`
left-joins X4's strategy series on **X4's own dates**, so the join matches nothing. **R1's path is
deliberately not edited.** The derived reading survives, and the **breakeven** is the figure to
quote because it needs no cost assumption — 33.4 bps was measured on the restricted universe and a
9,645-name book holds far smaller names.

---

## 5. WHAT THE MOVE CANNOT SETTLE, NAMED SO IT IS NOT MISTAKEN FOR DONE

* **`V6-B` stays `UNMEASURED`.** Its `C1` is a **gating** fidelity control that ABORTS, and its
  register 6.6 **voids every arm** behind it. It is deliberately not parameterised — `W-28`
  forbids relaxing a pre-committed bar after watching it fail — and its register's `C2` pins
  *"69 dates, 2,531 names"* independently. **Re-measuring `V6-B` on a corrected universe needs its
  own register.**
* **`S22`'s per-horizon `fixed_weights_null` floors stay `UNMEASURED`**, with the cost named: 200
  draws × 8 horizons on a 290k-row panel is many hours, and a reduced count is refused because a
  p95 over fewer than 100 draws is set by its top two values. **Only h63 has a corrected floor**,
  and comparing h>63 against it is the extrapolation S22 built its own nulls to avoid.
* **The Deflated Sharpe's `N` channel.** `sr0` is a direct function of trial count, so the DSR
  moves at **every** `N` and cannot be carried forward from any prior run. It must be recomputed
  in the canonical run and labelled with its `N`.

---

## 6. THE RISK THIS MEMO EXISTS TO BOUND

The move's failure mode is **not** a wrong number; it is a **silently changed object**. Three
specific shapes, each with the guard that catches it:

1. **The headline becomes the adopted book.** Caught by step 1's gate: the headline path must
   never consult CPCV, pinned on the syntax tree, with the adopted block required non-empty so
   the guard cannot pass by removing the feature.
2. **A corrected statistic is compared to an X7 floor.** Caught by importing the floors from
   `CORRECTED_FLOORS.json` rather than retyping, and by keeping X7's seven on the page labelled
   with their own object.
3. **A landed figure is carried forward unexamined.** Caught by the three-state vocabulary: a
   `SURVIVES` row cannot exist without a corrected value, and an `UNMEASURED` row cannot exist
   without a named reason.

**AND THE MOVE IS NOT A VINTAGE EVENT ON THE VINTAGE RULE'S OWN WORDING.** That rule defines
*"adopted"* as **"ships in the live scoring path"**. This changes which panel the canonical
research file measures; it does not change the hot list, the Index the site serves, or any number
a user receives through the live scoring path. **`S25-REPAIR` reached the same conclusion for the
same reason and routed the classification to Don rather than assuming it** — and that is what this
memo does too. **If Don judges it a vintage event, the clock resets and the move waits.**


---

## 7. HOW THE SWITCH IS MADE — and the obvious route is the wrong one

**MEASURED, BECAUSE IT CHANGES WHAT THE MOVE IS.** The canonical run is
`python -m valuation.edge.fundamental_panel`, and its `main` builds the provider from
**`CONFIG.wrds_data_dir`**, which is `_get("WRDS_DATA_DIR")` — an **`.env`** variable.

**SO THE OBVIOUS ROUTE — point `WRDS_DATA_DIR` at `data/full2009/backtest` — WOULD ALSO RE-POINT
THE LIVE SCREENER'S PROVIDER.** The same variable feeds the product's own data source, so that
edit is a construction change with a live blast radius rather than a research one. It is also a
file this lane may never read, print or overwrite, so it is not available in any case.

**THE ROUTE IS THE EXISTING `--data-dir` FLAG** (`fundamental_panel.py:4770`,
*"use local exported files (WRDS layout) instead of the API"*). That makes **"canonical" a
RUNBOOK fact — which invocation produces the canonical file — rather than an environment
change**, and it keeps the live path untouched by construction rather than by care.

**THE CANONICAL INVOCATION, written out so it is not reconstructed from memory:**

    python -m valuation.edge.fundamental_panel \
        --data-dir <repo>/data/full2009/backtest \
        --json <repo>/BACKTEST_RESULTS.json

**AND `BACKTEST_RESULTS.json` IS TRACKED AND IS OVERWRITTEN BY EVERY RUN**, so it is backed up
before the canonical run and the backup is diffed afterwards leaf by leaf. A run that overwrites
the project's memory without a diff is how a figure changes with nobody able to say which run
changed it.

**WHAT THIS DOES NOT DECIDE.** Whether `.env` should eventually point at the corrected export —
i.e. whether the LIVE product should score the wider universe — is **Don's call and a separate
one**, and nothing in this memo prepares it. `UNIVERSE-BIAS` and `TIERED-POOL` both measured that
reaching down the cap scale does not pay, and `STAGE1-BATCH2` has now added a third reading in
the same direction (B5 clears wide at *t* +2.4327 and reads +1.0578 on the tier). **So the
evidence currently argues against moving the live universe, and this move is deliberately only
about which panel the research file measures.**
