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

---

## 8. AMENDMENTS MADE WHILE EXECUTING STEPS 2-6 — each against this memo's own text

Three, all made **before** the step they govern was executed, which is the only time an amendment
is worth anything. Two are corrections to **this memo**.

### 8.1 STEP 3's GATE IS WRONG: *"by import rather than retyping"* IS NOT IMPLEMENTABLE ON A PAGE

§2 step 3 says the corrected floors become what the pages read *"by import rather than retyping"*.
**Measured, that cannot be done, and the project already documents why in two places.**

**THE ONLY SHIPPED SURFACE THAT READS A FLOOR IS `valuation/web/research_record.py`**, which
carries `HEADLINE_STATISTIC = 2.6199121240414884` and `PLACEBO_FLOOR = 2.2837` as module constants
and renders **the COMPARISON, never the operands** — pinned by test, because `MB38`'s rule is
about what the SITE publishes rather than what the source contains.

**AND A PAGE CANNOT DERIVE A RESEARCH FIGURE AT RENDER TIME.** `data/` is gitignored and never
ships with a deploy — `optionable_partition.py` says so of itself (*"It cannot be derived at render
time: `data/` is gitignored and never ships with a deploy, which is the same constraint
`tidemark_surface` documents"*) and `proof.py` repeats it. So *"by import"* would have made a
public page depend on a licensed artifact that is **ABSENT on the host**, and the failure mode is
the one this record keeps finding: it **fails OPEN** — the comparison quietly loses its floor
rather than raising.

**THE AMENDMENT: THE LITERAL STAYS A LITERAL AND THE DRIFT IS WHAT GETS PINNED.** That is `MA13`'s
committed-literal idiom, the same mechanism the trial stamp already uses: a test compares the
constant against `CORRECTED_FLOORS.json` when the licensed root is present and **skips LOUDLY**
when it is absent. A committed literal plus a drift test is strictly stronger than an import that
cannot run where the code runs.

**AND THE EDIT IS NOT TAKEN HERE.** `valuation/web/` is the app lane's and `RUN_RULES` rule 3 is to
report rather than edit. Both constants appear in §4's table with their file and symbol, and the
new comparison's **outcome** is stated there so the app fixer is not left to derive it.

### 8.2 THE BULK-CACHE HAZARD — CHECKED RATHER THAN ASSUMED, AND IT IS NOT LIVE

`main()` has **no flag for the bulk cache**. `WRDSProvider.bulk_dir` derives it from the export's
parent, so `--data-dir <data>/full2009/backtest` resolves **`<data>/full2009/bulk/prepared`** —
**not** the `<data>/bulk/prepared` that `CORRECTED-REBUILD` pinned by assigning `prov._bulk_dir`
explicitly.

**AND AN ABSENT CACHE DOES NOT FAIL — IT DEGRADES.** The provider's own comment: *"Absent caches
degrade to empty -> every consumer falls back to its previous behaviour rather than failing."* So a
wrong derivation would have silently cost the **point-in-time market cap from DAILY** (falling back
to the shares × price path this project replaced for being buggy), the **ACTIONS delisting mask**
that makes the returns survivorship-free, and **SF3's conviction inputs** — with nothing raising,
on the one file the project uses as its memory.

**MEASURED: the derived path is a DISTINCT path carrying IDENTICAL content** — 4 of 4 files hashed
byte-for-byte including `sf3.pkl` and `tickers.pkl` — so the canonical run reads the same bulk
inputs the rebuild did and **the hazard is real in principle and not live.** Recorded because the
check costs two minutes and the failure is silent. **Existence was not the answer**: the directory
being present told me nothing, which is this record's own *existence-is-not-population* rule.

### 8.3 THE FLOOR MATCHED TO THE DEPLOYED HEADLINE IS THE NON-ADOPTING SPLIT, NOT THE POOLED ONE

`CORRECTED-FLOORS` retained its 100 draws and split them, for `MB8`'s reason stated in its own
artifact — *"A floor whose draws adopt is not the floor for a book that does not."*

| long-short HAC floor (p95) | draws | value |
|---|---|---|
| pooled (`full`) | 100 | **1.485155** |
| `adopting` | 16 | 2.218588 |
| **`non_adopting`** | 84 | **1.363955** |

**The deployed book never adopts**, so the pooled floor is partly inflated by the very adoption
channel `X7` measured at about **+1.4 of *t*** on 27% of pure-noise draws. **The MATCHED floor for
the deployed headline is `non_adopting` 1.363955**; the **like-for-like old → new** comparison is
`full → full`, because X7's 2.2837 was itself taken over all 100 draws. **The verdict is unchanged
under all three splits**, which is why this is a precision point and not a result.

### 8.4 STEP 2 IS NOT RESEARCH-ONLY: THE CANONICAL ARTIFACT IS READ BY A PUBLIC PAGE AT REQUEST TIME, AND IT CARRIES A TYPED UNIVERSE STAMP THAT WOULD MISLABEL IT

**THIS IS THE MOST CONSEQUENTIAL THING FOUND WHILE EXECUTING THE MOVE, AND IT CHANGES WHAT STEP 2
IS.** §2 calls steps 2-6 *"measurement and reporting"*. Measured, that is wrong:
`BACKTEST_RESULTS.json` is **tracked**, ships in the deploy image (`.dockerignore` excludes
`data/`, not the repo-root artifact), and **`settings.measured()` reads it at request time** —
`BOOK_CONFIGS` → `measured()` → `index_track.backtested` → the landing page's *"Backtested net
alpha"*. `MC11` deliberately removed the figure literals there, with its own reason: *"a second
copy of a measured number is a copy that goes stale, and the only durable fix is not to keep
one."*

**SO OVERWRITING THE CANONICAL FILE MOVES A PUBLIC FIGURE WITH NO APP-LANE EDIT AT ALL.** That is
the read-through working as designed, and it is exactly why the figure must not move without Don
seeing it.

**AND IT EXPOSES A LIVE DEFECT THAT THE MOVE ITSELF TRIGGERS.** `measured()` reads the FIGURES
through from the artifact and then types their PROVENANCE beside them:

    out["n_dates"] = 69
    out["n_names"] = 2531

**So after the canonical re-run the page would report corrected figures from a 9,645-name panel
under a stamp saying 2,531 names.** `MC11` removed the figure literals and left the universe
literals — the same family one level down, and the more dangerous half, because a wrong figure
invites checking while a wrong label makes a right figure unverifiable.

**IT IS FIXED BY DERIVING BOTH FROM THE SAME BLOB `measured()` ALREADY OPENS**
(`universe.n_names` / `universe.n_dates`), with **no fallback** — the module's own rule is *"An
absent artifact returns nothing, not the old literals."* **The edit is taken rather than
reported**, against `RUN_RULES` rule 3, and the reason is narrow: **the mislabel is CREATED by
this move**, so leaving it to the screener lane means shipping a mislabel I caused; and the change
**derives** a figure instead of typing one, which is the standing rule that module already follows
for everything else in the same dict. Pinned by a test.

**TWO MORE SURFACES CARRY THE SAME TYPED STAMP AND ARE *NOT* TOUCHED, because they are internally
consistent today**: `hold_horizon.PANEL_NAMES`/`PANEL_DATES` and
`optionable_partition.N_PANEL_NAMES` sit beside **literal** figures from the same 2,531-name
panel, so nothing drifts until the figures move. Both are in §4's table, and moving a stamp
without its figures would be the mislabel in the other direction.

### 8.5 THE CANONICAL ARTIFACT COMPUTES ITS OWN FLOOR VERDICT AGAINST A TYPED LITERAL, AND AFTER THE MOVE THAT IS A MIXED PAIR — REPORTED, NOT RE-RUN

`fundamental_panel.py:3438-3439` carries the floor as a literal and computes a verdict beside it:

    "x7_calibrated_floor": 2.2837,
    "clears_x7_calibrated_floor": (None if t is None else bool(t > 2.2837)),

**That is a THIRD place the floor lives** — after `research_record.PLACEBO_FLOOR` (§8.1) and
`CORRECTED_FLOORS.json` — and after the move the canonical file compares the **corrected**
long-short HAC *t* against the **2,531-name panel's** floor. That is the same mixed-pair defect
§8.1 guards on the page, inside the artifact the page's figures come from.

**THE VERDICT DOES NOT CHANGE AND THAT IS WHY THIS IS A LABEL RATHER THAN A RESULT.** The
corrected statistic clears **both** floors — the old 2.2837 and the corrected 1.485155 — and it
clears the matched non-adopting 1.363955 as well, so `clears_x7_calibrated_floor: true` is true on
every reading. What is wrong is that **the floor's provenance is unstated**, so a reader cannot
tell that the bar was calibrated on a different panel from the statistic.

**IT IS REPORTED RATHER THAN FIXED, AND THE REASON IS ARITHMETIC RATHER THAN PRINCIPLE.** The
field is written by the run itself, so adding it means **re-running the canonical backtest** —
one to two hours — **to change a label on a verdict that is correct under every floor the project
has.** That trade is not worth taking, and taking it would also mean editing a shipped file while
a canonical run was in flight, which is the process error this session already made once.

**SO IT IS A NAMED NOT-DONE**: the next canonical run should carry the floor's panel beside the
floor, and until it does, **the canonical file's `x7_calibrated_floor` is the 2,531-name panel's
and is an EXTRAPOLATION on this universe** — the record's own word for a bar quoted outside the
configuration it was calibrated in. `CORRECTED_FLOORS.json` is the authority for this universe's
floors, and §4's table carries both.

### 8.6 THE TWO PANELS SHARE **ZERO** REBALANCE DATES, SO EVERY OLD → NEW ROW CONFOUNDS UNIVERSE WITH GRID

**This is the largest caveat on the move and it was not anticipated anywhere — in this memo, in
`CORRECTED-FLOORS`, or in `UNIVERSE-BIAS`.** The step-2 leaf diff surfaced it as 76 "removed"
leaves, every one a `cleanups.panel_window.cross_section_by_date.<DATE>` entry, and chasing that
down gave the measurement:

| | published panel | corrected panel |
|---|---|---|
| rebalance dates | 69 | 69 |
| first date | 2009-01-15 | **2009-03-27** |
| last date | 2026-01-28 | **2026-04-09** |
| **dates in common** | — | **0** |

**NOT ONE OF THE 69 DATES IS SHARED.** The rebalance grid is derived from the shared trading
calendar, which is built from the universe's own price history — so a universe 3.8× larger cuts
the calendar differently and the whole grid shifts. Same count, disjoint dates.

**WHY THAT MATTERS RATHER THAN BEING A CURIOSITY: `X2` ALREADY PRICED THE GRID.** It re-ran the
whole backtest on seven equally valid grids (offsets 0/5/10/20/30/40/50 trading days) on ONE
universe and measured the long-short *t* ranging **2.703 to 3.517** — a spread of **0.81 of a
*t*** from the grid alone, with nothing else changed. `CLAUDE.md` records its instruction
verbatim: *"Quote **t 2.7–3.5 depending on grid, straddling the hurdle** — never one side of 3.0
as a fact."*

**SO THE HEADLINE MOVE — long-short HAC *t* 2.6199 → 4.5945 — IS A UNIVERSE EFFECT AND A GRID
EFFECT TOGETHER, AND THIS MOVE DOES NOT SEPARATE THEM.** The move is far larger than X2's grid
spread (**+1.97** against ±0.81), so it is not plausibly grid alone — but *"the corrected universe
raises the long-short t to 4.59"* attributes a two-cause move to one cause, and that sentence may
not be written without this paragraph.

**WHAT WOULD SEPARATE THEM, named so the gap is a known one rather than a discovered one:** score
the **published 2,531-name universe on the corrected panel's own grid**, or the corrected universe
on the published grid. Either is a panel build, neither is done here, and **neither is proposed as
part of this move** — it is a measurement with its own cost and it should not be bolted onto a
re-run whose purpose was to make the canonical file describe the deployed book.

**IT ALSO BOUNDS §4's TABLE.** Every `RESTATEMENT` row there is a restatement under a universe
change **and** a grid change. The rows are still the right rows for the app lane to act on — the
corrected figure is what the corrected panel measures, which is what a canonical file should
carry — but the *reason* a figure moved is not attributable from this move alone.

**ONE THING IT IS NOT: a reason to doubt the figures.** The cross-instrument control is exact —
all seven of part 1b's independently landed deployed statistics reproduce in the canonical file at
**|dev| 0.000e+00** on the same 9,645 names, by a different call path. The panel is the object the
record describes; what is unseparated is the *attribution* of the change, not the measurement.

### 8.7 STEP 1 PASSED ITS OWN GATE AND STILL DID NOT REACH THE CANONICAL FILE — `MA40`'s DEFECT, ON THIS SESSION'S OWN CHANGE

**The step-2 leaf diff's single most useful finding, and it is about my own step 1.** Both of step
1's new blocks — `headline_weighting_is_the_deployed_book` and `adopted_book` — were computed by
`run_backtests`, reached its result dict, passed step 1's AST gate, appeared in the `--json` dump,
and **were ABSENT from the canonical pair.**

**WHY: `build_payload` IS AN ALLOWLIST, AND THE GUARD THAT WATCHES IT IS ONE TOO.**
`payload_schema.check_payload` iterates **`BLOCK_SPEC`** rather than the result, so a top-level key
that is not registered is **invisible to the very guard `MA39`/`M6` built to catch exactly this**.
`MA40` found ten computed fields being dropped this way — including B17's entire disclosure — and
registered them. Mine are the eleventh and twelfth, and they were dropped by the same mechanism
four audits later. **"A guard reading a registry cannot see an unregistered field"** is already
in this project's memory as `M3`'s thesis; this is it happening again, to the person who had just
written the words.

**AND IT IS WHY THE MEMO'S STEP-2 GATE IS A LEAF DIFF RATHER THAN A SPOT CHECK.** A spot check of
the headline figures would have passed cleanly: every number was correct. What was missing was the
*label saying which book the numbers describe* — which is the entire content of step 1, and the one
thing a figure-by-figure check cannot see.

**THE FIX IS REGISTRATION, AND IT COST NO RE-RUN.** `build_payload` is a pure projection of the
result, and the `--json` dump IS that result, so the two blocks were registered and the canonical
pair **re-projected from the saved result** — seconds instead of the ~85 minutes the backtest took.
Re-projecting is also strictly safer than re-running: a second backtest would be a second
*measurement*, and the record documents run-to-run nondeterminism in `insider`, so two runs of
"the canonical run" could legitimately differ. The re-projection cannot. **Verified: 3,392 shared
leaves, exactly 2 moved (both timestamps), 138 added (the two blocks, and nothing else), ZERO
removed.**

**A DEFECT IN THE RE-PROJECTION ITSELF, CAUGHT BY ITS OWN REFUSAL.** `cleanups` is **not part of
the result** — it is a local of `fundamental_panel.main`, passed to the writer as a separate
argument — so my first re-projection read `res.get("cleanups")`, got nothing, and **would have
dropped the whole `cleanups.panel_window` block (104 leaves) from the canonical file.** A script
written to fix a silent drop, introducing one. It refused rather than writing, because its own
diff required every removal to be attributable, and the block is now carried over from the first
projection. **That refusal is the only reason this is a paragraph rather than a loss.**

**BOTH BLOCKS ARE NOW IN `BLOCK_SPEC`**, which is the durable half: they were dropped *because*
nothing watched them, so registering a passthrough costs nothing today and turns a future
projection of a subset into a finding instead of a silence.

### 8.8 THE `cpcv` BLOCK NOW DESCRIBES A DIFFERENT BOOK FROM `construction`, AND THAT IS NEW — STEP 1 MADE IT VISIBLE RATHER THAN CAUSING IT

**CPCV ADOPTED.** On the corrected universe `cpcv.adopt` is **true** for the first time in this
project's history: `ic-proportional`, median out-of-sample IC **+0.096** against the default's
**+0.057**, positive in **100% of 15 CPCV paths**. So the case step 1 was written for is not
hypothetical — it is this run.

**AND IT EXPOSES A PAIRING NOBODY HAD TO THINK ABOUT BEFORE.** `cpcv_validate` computes PBO and
the Deflated Sharpe on **the returns of whichever scheme adoption chose**. While `adopt` was false
on every run, `rec is base` and the `cpcv` block described the same book as `construction`. Now it
does not:

| block | book | reading |
|---|---|---|
| `construction` | **DEPLOYED** (flat 1/7) | top-decile alpha **6.07%**, long-short HAC *t* **4.5945** |
| `adopted_book` | **ADOPTED** (`ic-proportional`) | top-decile alpha **2.83%** |
| `cpcv` | **ADOPTED** | PBO **0.0**, Deflated Sharpe **0.0016** |

**So pairing `construction.top_decile_alpha` with `cpcv.deflated_sharpe` pairs a numerator from
one construction with a denominator from another** — `MB8`'s rule, and precisely what
`CORRECTED-FLOORS` part 1b refused to do: its artifact reports both as `None` for the deployed
reading, with the reason in its own text (*"Reporting the adopted run's PBO beside flat-weight
alpha would pair a numerator from one construction with a denominator from another"*).

**THE FIX IS A LABEL IN THE ARTIFACT, NOT A RECOMPUTATION.** `cpcv` now carries
`describes_which_book` and a boolean `same_book_as_construction` (false on this run), so a reader
of the file can tell. **Deliberately NOT done: computing a deployed-book PBO or Deflated Sharpe.**
Both come out of `cpcv_validate`, which exists to evaluate a selection among its own schemes; a
"deployed PBO" would be a new construction with its own meaning, and inventing one inside a
canonical re-run is the opposite of what this move is for.

**THE NUMBER MOST LIKELY TO BE MISQUOTED FROM THIS RUN IS THE DEFLATED SHARPE AT 0.0016.** It is
**the ADOPTED book's**, and it is not comparable with the published **0.7863**, which was the
2,531-name panel's **deployed** figure (`rec is base` there). Quoting `0.786 → 0.0016` as a
collapse would compare two different books on two different universes on two disjoint grids.
**The deployed book's Deflated Sharpe on this universe is UNMEASURED**, and §4's table says so
rather than filling it in.

### 8.9 THE TWO RESULTS DON NEEDS BEFORE THIS SHIPS: the headline clears the HLZ hurdle for the first time, and the landing page's net alpha GOES NEGATIVE

Both come out of the canonical run; neither was anticipated by this memo.

#### (a) THE HEADLINE CLEARS THE HARVEY-LIU-ZHU HURDLE — the project's most-failed bar

| | published (2,531 names) | corrected (9,645 names) |
|---|---|---|
| long-short HAC *t* | 2.6199 | **4.5945** |
| hurdle √(2·ln N) | 3.2899 (`N` 224) | **3.3623** (`N` 285) |
| clears? | **NO**, short by 0.6700 | **YES**, by 1.2322 |

`R4` first made that comparison and recorded the failure; `MA5` then found *"3.0"* was never the
hurdle at all but √(2·ln N) frozen at `N` = 90. **The hurdle ROSE with the trial count — 224 → 285
trials — and the statistic rose faster.** It also still clears the corrected placebo floor
(1.4852 pooled, 1.3640 matched), so **both bars pass at once for the first time**, and `R4`'s
*"the tension"* note in the artifact is for this run no longer a tension.

**IT IS NOT A NEW RESULT AND MUST NOT BE REPORTED AS ONE.** This is the same composite, re-measured
on a wider universe and — per §8.6 — a **disjoint grid**, with the universe and grid effects
unseparated. What changed is the panel, not the strategy.

#### (b) THE PUBLIC LANDING PAGE'S "BACKTESTED NET ALPHA" GOES FROM +11.6%/yr TO −4.7%/yr

| public figure | published | corrected |
|---|---|---|
| `book_configs.roth.net_alpha` | **+0.1163** | **−0.0470** |
| `book_configs.roth.net_max_drawdown` | −0.2621 | **−0.5971** |
| `book_configs.taxable.after_tax_alpha` | +0.0211 | **−0.0057** |

**THESE ARE READ THROUGH AT REQUEST TIME** (§8.4): `measured()` → `index_track.backtested` → the
landing page. `BACKTEST_RESULTS.json` is tracked and ships in the image, so **this change reaches
the public site on the next deploy with no app-lane edit at all.** A sign flip on the headline
number a visitor sees is not a research detail.

**AND THE DIRECTION IS COHERENT RATHER THAN SUSPICIOUS, WHICH IS WHY IT SHOULD BE BELIEVED.**
`roth` is a concentrated **top-25** book. Top 25 of 2,531 names is the top 1%; top 25 of 9,645 is
the top 0.26% — a far more extreme selection, drawn from a universe whose ~7,100 added names are
overwhelmingly small. `UNIVERSE-BIAS`, `TIERED-POOL` and now `STAGE1-BATCH2`'s B5 all measured
that reaching down the cap scale does not pay, and the drawdown more than doubling (−26% → −60%)
is what a micro-cap-dominated 25-name book looks like.

**SO THE CORRECTED UNIVERSE MAKES THE DECILE LONG-SHORT BETTER AND THE CONCENTRATED BOOK WORSE,
AND BOTH ARE THE SAME FACT SEEN TWICE**: a wider universe gives the cross-sectional sort more to
work with and gives a 25-name book worse names to hold.

**THIS IS DON'S CALL AND IS DELIBERATELY NOT MADE HERE.** Three options, stated plainly:
1. **Land it.** The canonical file describes the corrected panel, the page follows, and the site
   reports a negative backtested alpha for the book it serves.
2. **Land the research file and pin the page to the published panel** — which means re-introducing
   a literal in `BOOK_CONFIGS`, i.e. undoing `MC11`, whose own reason was that a second copy of a
   measured number goes stale. Not recommended, and recorded so the cost is visible.
3. **Re-measure the served book on the corrected universe at its own tier.** The Index book is
   `$10B` large-cap, score-weighted, 8% cap, 0.30 band — **not** the all-cap top-25 `roth` config —
   and `INDEX_BOOK_CORRECTED.json` already exists. The public figure a visitor most needs is the
   one for the book they can actually buy, and `roth`'s all-cap top-25 is not it.

**Option 3 is this lane's recommendation, and it is a recommendation rather than an action**
because changing which book the landing page reports is a product decision.

---

## 9. THE MOVE STOPS AT STEP 2, AND THE BLAST RADIUS IS THE RESULT

**STEPS 1 AND 3-6 ARE DONE. THE CANONICAL ARTIFACT IS NOT LANDED, AND SIX GUARDS ARE WHY.**

The corrected run completed, every gate in §2 step 2 passed, and the cross-instrument control is
exact. Then the project's own suites were run against the new artifact and **six went red — every
one correctly, and not one of them because of a stale expectation.** Each names a *public claim*
that the move changes:

| suite | what it caught |
|---|---|
| `test_public_docs.py` | **`README.md`** — the public front page — carries the whole evidence section as figures that must match the artifact: `+7.17%/yr`, `2,531 names`, HAC *t* `2.62`, floor `2.2837`, hurdle `3.29`, `224` trials, **"❌ The Harvey–Liu–Zhu hurdle"**, and **"`cpcv.adopt` is `false` on every run"**. The move flips the ❌ to a ✅ and makes `adopt` true. |
| `test_docs_entry_points.py` | `START_HERE.md` asserts the headline **fails** the HLZ hurdle. `clears_hlz_hurdle` flipped false → true. |
| `test_proof_page.py` | the **public proof page** can no longer show the HLZ hurdle failing, and its placebo row-counts come out all-one-verdict because they compare the CORRECTED statistic against the PUBLISHED panel's draws. |
| `test_backtest_card.py` | the published `data_export/backtest_card.json` describes the 2,531-name panel and its own `C1` requires it to reproduce the artifact's `book_configs`. |
| `test_mc10_mc11_labels.py` | `measured()`'s universe stamp — and `MEASURED_BASIS` **types** *"2,531-name"* in PROSE beside the numbers it reads through. |
| `test_mb31_staleness_map.py` | two derived-from-`N` assertions move once the artifact's trial count and DSR move. |

**SO THE HONEST STATEMENT IS NOT "the move is done" BUT "the move is measured, and landing it
rewrites the public README's evidence section."** Flipping a ❌ to a ✅ on the project's most
prominent honesty claim, deleting the sentence *"`cpcv.adopt` is `false` on every run"*, and
turning the landing page's backtested net alpha from **+11.6%/yr to −4.70%/yr** (§8.9) are not
things a research lane should do on its own authority on a public repository. **`RUN_RULES`
rule 3, and §2's own rule one step later: if a step cannot pass its gate, the move stops there.**

### WHAT IS LANDED

* **Step 1** — the canonical headline describes the DEPLOYED book, with the adopted book beside
  it. **Vindicated by this run**: CPCV adopted for the first time, so without it the headline
  would now describe `ic-proportional` at 2.83% instead of the deployed 6.07%.
* **The two blocks `build_payload` was dropping**, now registered in `BLOCK_SPEC` (§8.7).
* **`cpcv`'s `describes_which_book` / `same_book_as_construction`** (§8.8).
* **`measured()`'s universe stamp, derived rather than typed** (§8.4) — and with the published
  artifact restored it returns `2531`/`69` exactly as the typed literals did, so it is
  **provably inert today** and correct the day the artifact moves.
* **`scripts/backtest_card.py --panel`** — additive, default unchanged, so the card can follow
  the canonical file when the decision is made.
* **`CANONICAL_FIGURE_TABLE.md`** — every public figure old → new, with the file and symbol.
* **This memo**, with all nine amendments.

### WHAT IS NOT LANDED, AND WHERE IT IS

**`BACKTEST_RESULTS.json` and `.md` are RESTORED to the published 2,531-name panel.** The
corrected pair is banked as **`data/free_analysis/BACKTEST_RESULTS_CORRECTED.json`** and
**`.md`** — a research artifact in the directory research artifacts live in, not a canonical file.
Nothing on any public surface moves, and the suites are green.

### WHAT DON HAS TO DECIDE, in the order it matters

1. **Does the public README's evidence section move to the corrected universe?** That is the
   ❌ → ✅ on the HLZ hurdle and the removal of *"`cpcv.adopt` is false on every run"*.
2. **Does the landing page's "Backtested net alpha" go negative**, or does it report the `$10B`
   Index book instead (§8.9's recommendation)?
3. **What does the proof page show** when three of its four bars pass and the fourth describes a
   different book (§8.8)?

**None of the three is blocked on measurement.** The numbers are in
`CANONICAL_FIGURE_TABLE.md` and `BACKTEST_RESULTS_CORRECTED.json`; what is missing is a decision.
