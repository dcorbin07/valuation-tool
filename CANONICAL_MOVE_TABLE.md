# CANONICAL MOVE — every public figure, old → new

**For the app-fixer lane, and for Don.** r1 landed the move's measurement; this table is the
hand-off. **The tracked `BACKTEST_RESULTS.json` is DELIBERATELY NOT SWAPPED** — the app fixer lands
the artifact swap and every page change in **one commit**, so the public site never shows new
numbers under old words (Don, 2026-10-07: *restate once, no interim patch*).

* **New numbers:** `data/free_analysis/BACKTEST_RESULTS_CORRECTED.json` (+ `.md`)
* **Index book:** `INDEX_BOOK_CORRECTED.json` · **floors:** `CORRECTED_FLOORS.json` ·
  **placebo draws:** `PLACEBO_CORRECTED.json` · **proof rows:** `CANONICAL_PROOF_ROWS.json`
* **Reasoning and the nine amendments:** `DECISION_canonical_move.md`

---

## 0. THE CAVEAT EVERY ROW BELOW INHERITS

**THE TWO PANELS SHARE *ZERO* REBALANCE DATES.**

| | published | corrected |
|---|---|---|
| names | 2,531 | **9,645** |
| rebalance dates | 69 | 69 |
| first / last | 2009-01-15 / 2026-01-28 | **2009-03-27 / 2026-04-09** |
| **dates in common** | — | **0** |

The grid is derived from the universe's own trading calendar, so a 3.8× wider universe shifts
every date. **`X2` measured the grid ALONE moving the long-short *t* by 0.81** (2.703–3.517 across
seven equally valid offsets on one universe). **So NO old → new change below is attributable to
the universe alone** — universe and grid moved together and this move does not separate them.
Separating them needs the published universe on the corrected grid, or vice versa; neither is done.

**EVERY FIGURE IS THE DEPLOYED EQUAL-WEIGHT BOOK (flat 1/7)** per Don's ruling — never the
CPCV-adopted one. That label is load-bearing for the first time: **CPCV ADOPTS `ic-proportional`**
on this universe (median OOS IC +0.096 vs the default's +0.057, positive in 100% of 15 paths), and
the adopted book's top-decile alpha is **2.83%** against the deployed **6.07%**.

**TWO NUMBERS THAT WILL BE MISREAD IF QUOTED BARE:**

1. **The corrected GROSS alpha (6.0674%) and the published NET alpha (6.0697%) both round to
   "6.07%".** They are different quantities on different panels. A restatement that writes "6.07%"
   is ambiguous — say *gross* or *net*, every time.
2. **`cpcv.pbo` and `cpcv.deflated_sharpe` describe the ADOPTED book**, not the deployed one, because
   `cpcv_validate` scores whichever scheme adoption chose. The artifact now carries
   `cpcv.same_book_as_construction` (**false**) to say so. The deployed book's PBO and Deflated
   Sharpe are **UNMEASURED** and must not be filled in from the `cpcv` block.

---

## 1. `README.md` — the public evidence section · **transcribed LITERALS**

| figure | old | new | book | caveat it must carry |
|---|---|---|---|---|
| universe | 2,531 names × 69 dates | **9,645 × 69** | — | disjoint grids (§0) |
| top-decile alpha, **gross** | +7.17%/yr | **+6.07%/yr** | deployed decile | not the Index; name the universe (DECISIONS 2026-10-02) |
| top-decile alpha, **net of costs** | +6.07%/yr | **+2.54%/yr** | deployed decile | the headline tradeability number; **fell 3.53pp** |
| cost breakeven vs measured | 134.1 vs 33.4 bps (**4.0×**) | **123.5 vs 77.0 bps (1.6×)** | deployed decile | measured cost **more than doubled** — the added names are small and illiquid |
| vs SPY total return | +9.99%/yr | **+4.02%/yr** | deployed decile | no "beats SPY" phrasing (DECISIONS) |
| long-short spread | +11.04%/yr, HAC *t* **2.62** | **+18.10%/yr, HAC *t* 4.59** | deployed decile | long-short is **not** the product; the Index is long-only |
| decile ordering | −0.89 | **−0.96** | deployed decile | −1.0 is a perfect ladder |
| placebo-calibrated floor | 2.2837 | **1.4852** pooled / **1.3640** matched | deployed decile | the matched floor is the non-adopting split — the deployed book does not adopt (`MB8`) |
| **Harvey-Liu-Zhu: ❌ → ✅** | 224 trials, hurdle 3.29, **falls short by 0.67** | **285 trials, hurdle 3.3623, CLEARS by 1.23** | deployed decile | **the hurdle ROSE and the statistic rose faster.** Not a new result — same composite, wider universe, disjoint grid |
| Deflated Sharpe | 0.79 vs >0.95; clears placebo 0.66 | **0.0016 (ADOPTED book)**; placebo floor 0.5912 | **ADOPTED** | **NOT comparable to 0.79** (different book, universe and grid). The deployed DSR is **UNMEASURED** |
| PBO | 73.3% (noise sits at 46.7%) | **0.0% (ADOPTED book)** | **ADOPTED** | same caveat as the DSR |
| *"`cpcv.adopt` is `false` on every run"* | true | **FALSE — it adopts `ic-proportional`** | — | the sentence must go; the flat 1/7 weights **stay** (Don: prove before changing) |
| trial counts | `N` = 224 equity / 292 options | **293 / 310** (285/310 at the corrected run; batch 3 then booked 8) | — | `N` moves whenever a register lands — derive it, never quote it |
| FF5+MOM unexplained | +6.99%/yr (NW *t* 3.98) | **+5.94%/yr (NW *t* 4.45)** | deployed decile | R1's own net-of-cost path is **UNMEASURED**; this is the gross intercept |
| *"400 half-universe books, not one negative"* | — | **UNMEASURED** | — | `X1` was not re-run on this universe; the sentence may not be restated, only removed or marked |
| Japan *t* 3.85 / Europe *t* 4.30 | unchanged | **unchanged** | JKP factors | `X8` is a different vendor and universe — untouched by this move |

---

## 2. `START_HERE.md` — two headline bullets · **LITERALS**

Same figures as §1 (alpha, long-short *t*, both floors, the HLZ direction, the universe line).
**Its guard pins BOOLEANS, not values**, deliberately — `clears_hlz_hurdle` flipped false → true,
which is what turned it red. Update the bullets and the booleans follow.

---

## 3. `/proof` (`valuation/web/proof.py`, `templates/_proof_body.html`)

### 3a. The four threshold bars · **LIVE READ** of `BACKTEST_RESULTS.json`

| bar | old | new | book |
|---|---|---|---|
| long-short *t* vs placebo floor | 2.6199 vs 2.2837 — **passes** | **4.5945 vs 1.4852 — passes** | deployed |
| long-short *t* vs HLZ hurdle | 2.6199 vs 3.2899 — **FAILS** | **4.5945 vs 3.3623 — PASSES** | deployed |
| PBO | 0.7333 — **FAILS** | **UNMEASURED** — Don, 2026-10-10 ↯ | deployed: not computed |
| Deflated Sharpe | 0.7863 — **FAILS** | **UNMEASURED** — Don, 2026-10-10 ↯ | deployed: not computed |

**SO THE PAGE GOES FROM THREE FAILING BARS TO NONE: two passes and two UNMEASURED.** The corrected
`cpcv` values (PBO 0.0, DSR 0.0016) describe the **ADOPTED** book and are therefore not shown
beside deployed figures — §0 point 2 and ruling 2 below. **A page with no failing bar must not read
as a page that passed everything**: the two unmeasured cells are the honest statement, and they
need their reason on the page (`cpcv_validate` scores whichever scheme adoption chose, and the
deployed book does not adopt).

### 3b. The four placebo rows · **LIVE READ** of the draws file (`CANONICAL_PROOF_ROWS.json`)

`n_beaten` is COUNTED from the 100 retained draws, ties counting against the strategy.

| row | old real / beaten | new real / beaten | matched (84 non-adopting) |
|---|---|---|---|
| top-decile alpha | 0.0717 / **0 of 100** | 0.0607 / **0 of 100** | 0 of 84 |
| top-decile alpha *t* | 4.3762 / **0 of 100** | 4.4127 / **0 of 100** | 0 of 84 |
| long-short *t* | 2.6199 / **3 of 100** | 4.5945 / **0 of 100** | 0 of 84 |
| decile ordering | −0.8909 / **1 of 100** | −0.9636 / **0 of 100** | 0 of 84 |

### ↯ RULING 2 — SHOW THE BLOCK AS IT IS, AND CHANGE WHAT THE GUARD REQUIRES

**Don, 2026-10-10** (relayed; `DECISIONS.md` entry pending): **show `/proof`'s placebo block as it
is on the corrected panel's own draws; change the guard to require a LIKE-FOR-LIKE comparison
rather than at least one failure; show PBO and the Deflated Sharpe as UNMEASURED.** Three
consequences, in the order the app lane will hit them:

* **The `real` side must come from `CORRECTED_DEPLOYED.json`, not from the sweep.**
  `PLACEBO_CORRECTED.json`'s own `real` leg is the **CPCV-ADOPTED** book
  (`long_short_tstat_nw` **2.1238**), so pointing the page at it would publish the adopted book
  under the deployed book's words — against Don's 2026-10-07 ruling. **Only the DRAWS come from
  the sweep.** "Like-for-like" is exactly this: the real value and the draws must describe the
  same book, the same universe and the same grid.
* **The guard's assertion changes, and it is a strengthening rather than a relaxation.**
  `test_proof_page` currently asserts `any(swept) and not all(swept)` — *"every placebo row has
  the same verdict"* — which fires on the corrected panel because **all four rows sweep (0 of 100
  beaten)**. The new requirement is that each row's real value and its draws be the same object;
  that is a property of the **comparison**, which is checkable, where "at least one row must fail"
  was a property of the **outcome**, which the data decides. **A guard keyed on an outcome is a
  clock** — this record's own recurring defect — so this swap moves it onto the right axis.
* **PBO and the Deflated Sharpe are shown as UNMEASURED** on the deployed book (see §0 point 2),
  rather than carrying the ADOPTED book's 0.0 and 0.0016 beside deployed figures. **That removes
  the last failing bar from §3a**, so the page's four-bar block becomes two passes and two
  unmeasured — and the honest mix now lives in the *unmeasured* label rather than in a failure.

**WHAT THE PAGE MAY NOT SAY AS A RESULT.** With every placebo row sweeping and both overfitting
statistics unmeasured, nothing on this block is a demonstrated failure — so the page must not
imply the model has been tested against overfitting and passed. `UNMEASURED` is the claim, and the
reason (`cpcv_validate` scores whichever scheme adoption chose) belongs beside it.

### 3c. Prose · **TEMPLATE LITERAL**, `_proof_body.html:456`

| sentence | action |
|---|---|
| *"companies that went bankrupt or were delisted stay in, so the record is not a survey of survivors"* | **Replace with an accurate description of the corrected universe** (Don, 2026-10-07). Survivorship-freeness is still true; what changes is that the panel is now the full raw export (9,645 scored names of 17,053) rather than a 2,531-name subset |
| *"Top-decile alpha, per quarter"* (label on the §3b row) | **Reported, not fixed:** the artifact's value is **annual**, and both sides of the comparison are annual, so the count is right and the LABEL is wrong. Pre-existing; the app lane's copy |

---

## 4. The Index tab · `valuation/screener/index_book_measured.py` · **committed LITERALS**

Source: `INDEX_BOOK_CORRECTED.json` `arms.A_served` / `tax_treatments` / `contract_power_input`.
Every literal is pinned by `test_index_book_measured` to appear verbatim in `HANDOFF_edge_audit.md`
**and** `VALQUO_LEDGER.md` — so the record must carry the new values or the module goes red.

| symbol | old | new |
|---|---|---|
| `PANEL` | "2,531-name point-in-time panel, 69 quarterly dates" | **"9,645-name …, 69 quarterly dates"** |
| `SERVED_NET_PCT` | 17.1817 | **18.0403** |
| `SERVED_SHARPE` | 1.0318 | **0.9694** |
| **`SERVED_MAXDD_PCT`** | −23.06 | **−28.997** ← Don's *"deeper Index drawdown"* |
| `SERVED_TURNOVER` | 2.4372 | **2.8094** |
| `SERVED_COST_BPS_ONE_WAY` | 9.58 | **9.4356** |
| `SERVED_ROTH_PCT` | 17.1619 | **18.0169** † |
| `SERVED_ROTH_SHARPE` | 1.0318 | **0.9694** ‡ |
| `SERVED_ROTH_MAXDD_PCT` | −23.03 | **−28.997** ‡ |
| `SERVED_TAXABLE_PCT` | 12.2033 | **12.5036** |
| `SERVED_TAXABLE_SHARPE` | 0.7595 | **0.6987** |
| `SERVED_TAXABLE_MAXDD_PCT` | −24.76 | **−30.537** |
| `TAX_COST_PP` | 4.9586 | **5.5133** |
| `SHORT_TERM_SHARE_PCT` | 84.08 | **90.353** |
| `SPY_PCT` | 15.23 | **15.8226** |
| `TAXABLE_VS_SPY_PP` | −3.03 | **−3.319** |
| `ALPHA_VS_OWN_TIER_PP` | 4.1209 | **4.6177** |
| `ALPHA_VS_SPY_PP` | 1.9488 | **2.2177** |
| ~~**`ALPHA_VS_ALL_CAP_EW_PP`**~~ | ~~−0.0576~~ | **DROPPED FROM THE TAB — Don, 2026-10-10** ↯ |
| `RESEARCH_NET_PCT` | 23.2893 | **14.6851** |
| `RESEARCH_ALPHA_VS_EW_PP` | 6.0500 | **2.5736** |
| **`RESEARCH_ALPHA_VS_SPY_PP`** | **+8.0564** | **−1.1374** ← sign flip |
| `RESEARCH_SHARPE` | 1.0997 | **0.7117** |
| `RESEARCH_MAXDD_PCT` | −28.48 | **−37.384** |
| `RESEARCH_TURNOVER` | 2.6066 | **2.4680** |
| `RESEARCH_COST_BPS_ONE_WAY` | 33.35 | **76.973** |
| `SERVED_TE_VS_SPY` | 8.4381 | **8.4296** |
| `SERVED_MONTHS_TO_DETECT` | 4383 | **3307** |
| `SERVED_YEARS_TO_DETECT` | 365 | **275.6** |

**EVERY ROW ABOVE WAS VERIFIED AGAINST THE PUBLISHED ARTIFACT BEFORE THE CORRECTED VALUE WAS
TAKEN** — all 22 literals reproduce their claimed source exactly on `INDEX_BOOK.json`, so the
corrected column comes from the same field and not from a lookalike. (My first pass had
`SERVED_ROTH_PCT` wrong, from `net_ann` rather than the Roth path; the check caught it.)

**† `SERVED_ROTH_PCT` is `roth_ira.gross_ann − roth_ira.total_drag_ann`**, which is why it differs
from `SERVED_NET_PCT` (18.0403) in the second decimal — the published pair differs the same way
(17.1619 vs 17.1817). Keep both routes, do not reconcile them.

**‡ The Roth risk figures take `A_served`'s `net_sharpe` / `net_max_drawdown`**, because the Roth
treatment IS net-of-costs-with-no-tax. The published literals differ from `SERVED_SHARPE` /
`SERVED_MAXDD_PCT` in the third decimal (−23.03 vs −23.06) by a routing difference the artifact
does not expose; the corrected pair inherits that, and no roth-specific drawdown is fabricated.

### ↯ RULING 1 — `ALPHA_VS_ALL_CAP_EW_PP` IS DROPPED FROM THE INDEX TAB

**Don, 2026-10-10** (relayed to this lane; the `DECISIONS.md` entry is pending and that file is
the Cowork manager's, so it is not edited here): **drop alpha versus the all-cap equal-weighted
universe from the Index tab, and show the Index against SPY and against the equal-weighted
`$10B` tier instead.** So the tab's two surviving comparisons are:

| what the tab shows instead | old | new |
|---|---|---|
| `ALPHA_VS_SPY_PP` — vs SPY | 1.9488 | **2.2177** |
| `ALPHA_VS_OWN_TIER_PP` — vs the equal-weighted `$10B` tier | 4.1209 | **4.6177** |

**WHY THE DROPPED FIGURE WAS THE MOST MISLEADING NUMBER IN THIS TABLE, recorded because it is the
reason for the ruling.** It moves −0.06pp → **+5.93pp**, which reads as the Index gaining 6pp of
alpha. **It did not.** The all-cap equal-weighted **BENCHMARK fell from 17.24%/yr to 12.11%/yr** —
**5.13pp of the ~5.99pp move** — while the book's own return rose 0.86pp, its drawdown deepened
5.9pp and its Sharpe fell. Both replacement comparisons are against benchmarks that do **not**
change composition with the universe (SPY is SPY; the `$10B` tier is a property of the name), so
neither can move for that reason.

**CONSEQUENCE FOR `INDEX-BOOK`'s VOID CONDITION, which must not be dropped by accident.** Its rule
is *"BOTH ALPHA SENTENCES ARE TRUE AND NEITHER MAY TRAVEL ALONE"* — written when one reading was
+4.12pp and the other ≈0. **Removing the all-cap leg removes one of the two sentences the rule
binds**, so the rule as written no longer has a second sentence to pair. It should be re-pointed to
the surviving pair (vs SPY **and** vs the tier, neither alone) rather than deleted: the disclosure
it exists for — never quote one comparison as though it were the whole picture — is unchanged.

### ↯ RULING 3 — SHOW THE RESEARCH DECILE'S −1.14pp/yr PLAINLY

**Don, 2026-10-10** (relayed; `DECISIONS.md` entry pending): **show the research decile's
−1.14pp/yr net versus SPY plainly.** No softening, no omission.

`RESEARCH_ALPHA_VS_SPY_PP` goes **+8.0564 → −1.1374**: the all-cap equal-weighted research decile
moves from **+8.06pp/yr over SPY to 1.14pp/yr UNDER it**, net of costs. Its months-to-detect goes
from 385 (32 years) to **never** — a negative edge is not detectable at any horizon — and its cost
per trade **more than doubled, 33.35 → 76.97 bps one-way**, which is where the swing comes from:
the ~7,100 names the corrected universe adds are small and dear to trade.

**THIS IS THE SHARPEST SENTENCE IN THE WHOLE MOVE AND IT IS NOW REQUIRED COPY.** On the corrected
full universe, the research decile every headline figure is drawn from **does not beat SPY after
costs.** It is also already covered by `DECISIONS.md` 2026-10-02 (any research-decile figure on a
public page must say in the same sentence that it is not the Index and name its universe) and by
the standing ban on "beats SPY" phrasing — which now cuts the other way and needs no exemption.

**WHAT IT DOES NOT SAY:** it is not a statement about the **Index**, which is the `$10B`
score-weighted book and reads **+2.2177pp/yr vs SPY** (§4). The two must not be conflated, and
that is precisely what the 2026-10-02 disclosure rule exists to prevent.

---

## 5. The landing tiles · `valuation/screener/settings.py` · **LIVE READ, no edit needed**

`BOOK_CONFIGS` → `measured()` → `index_track.backtested` → the landing page's *"Backtested net
alpha"*. `MC11` removed the literals on purpose, so **these move the moment the artifact is
swapped, with no page edit at all.**

| field | old | new | caveat |
|---|---|---|---|
| `book_configs.roth.net_alpha` | **+11.63%/yr** | **−4.70%/yr** | **a sign flip on the headline figure a visitor sees** |
| `book_configs.roth.net_max_drawdown` | −26.2% | **−59.7%** | more than doubled |
| `book_configs.taxable.after_tax_alpha` | +2.11% | **−0.57%** | sign flip |
| `measured()["n_names"] / ["n_dates"]` | typed `2531` / `69` | **DERIVED from the artifact** | already fixed by r1 at `d71c880`; provably inert on the published artifact |
| `MEASURED_BASIS` (prose) | *"full-universe **2,531-name** … EQUAL-WEIGHTED decile book"* | **must lose the typed count** | the figures read through and the prose did not — the dict would say `n_names: 9645` beside a 2,531 basis |

**WHY `roth` FLIPS, QUANTIFIED:** `roth` is a **top-25** book. Its cost **breakeven falls from
198.2 to 31.3 bps one-way while its measured cost rises to 77.0 bps** — the breakeven is now
**below** the actual cost, which is exactly what a negative net alpha means. Top-25-of-9,645 is the
top 0.26% of a universe whose ~7,100 added names are overwhelmingly small, and
`UNIVERSE-BIAS`/`TIERED-POOL`/`STAGE1-BATCH2`'s B5 all measured that reaching down the cap scale
does not pay.

**DON'S OPTION, RECOMMENDED BY THIS LANE:** report the **$10B Index book** on the landing tile
instead of the all-cap top-25 `roth` config. That is the book a visitor can actually buy, its
figures are in §4, and it does **not** flip sign. Changing which book the tile reports is a product
decision and is **not** made here.

---

## 6. Other surfaces the six red suites named

| surface | symbol | old | new | lives as |
|---|---|---|---|---|
| `valuation/web/research_record.py` | `HEADLINE_STATISTIC` | 2.6199121240414884 | **4.594456679049444** | literal, **never rendered** (`MB38`) |
| " | `PLACEBO_FLOOR` | 2.2837 | **1.485155** (pooled) | literal, never rendered |
| `valuation/web/hold_horizon.py` | 1-quarter alpha copy | 6.6%/yr | **6.07%/yr** | literal — **SURVIVES** (moves 0.53pp) |
| " | 2-year alpha copy | 5.1%/yr | **2.56%/yr** | literal — **NO LONGER HOLDS** (moves 2.54pp) |
| " | `RANK_IC_FIRST_QUARTER` / `_TWO_YEARS` | 0.0336 / 0.0655 | **0.0594 / 0.1017** | literal — the rise-with-horizon claim **SURVIVES** |
| " | `PANEL_NAMES` / `PANEL_DATES` | 2531 / 69 | **9645 / 69** | literal |
| `valuation/web/score_confidence.py` | `PER_NAME_DATES` | 45 of 69 (gate 42) | **12 of 69** | literal — **NO LONGER HOLDS**, and below the register's own gate |
| " | `GROUP_DATES` | 21 of 69 | **57 of 69** | literal — moves the other way; the limitation weakens |
| `valuation/web/optionable_partition.py` | `N_PANEL_NAMES` | 2531 | **UNMEASURED** | literal — `P1S0` was measured on the old panel and is **not** re-run; move the stamp only with its figures |
| `valuation/edge/fundamental_panel.py` | `x7_calibrated_floor` | 2.2837 (typed) | **unchanged, now an EXTRAPOLATION** | literal in the run — the verdict is true under all three floors, so a provenance label rather than a wrong result; a future run should carry the floor's panel |

**ALSO RESTATED BY THE MOVE (research record, not a public page):** `S22`'s shape statistic
`R_8` **6.195 (CONSTANT-RATE) → 3.372 (INTERMEDIATE)**; its *"alpha HAC *t* never below 3.16"*
**→ 3.0206** (the literal no longer holds, the substance — alpha separable at every horizon —
survives); its two-year *t* **3.83 → 3.3845**.

---

## 7. What this table does NOT do

* **It does not swap the tracked artifact.** That and every page edit land together, in one commit,
  by the app fixer.
* **It adopts nothing and changes no page.** The flat 1/7 weights stay (Don: *prove before
  changing*); CPCV adopting a scheme does not change them.
* **It does not touch `PAPER_TRACK_CONTRACT.md`'s frozen meter parameters or the forward record.**
* **It does not re-run `X1` (the half-universe split), `P1S0`, or R1's own net-of-cost path** —
  each is marked UNMEASURED above rather than restated from a neighbouring figure.
* **It makes no claim that any figure moved BECAUSE of the universe** — §0's disjoint grids forbid
  that attribution, and no row here asserts it.

---

## 8. ONE NOTE FOR THE TEST THE APP LANE IS ASKED TO WRITE

The app-fixer brief says *"a test should fail if any page still quotes a figure from the old panel
after the move."* **THIS FILE MUST BE EXEMPT FROM IT.** Quoting the old value beside the new one is
its entire purpose, so a blanket ban on old-panel figures in markdown would fire on the hand-off
document itself. There is precedent and it is the right shape:
`tests/test_docs_entry_points.py` already **exempts quotations**, for exactly this reason —
recording what a figure *used to say* is not the same as instructing from it. Scope the new test to
the **rendered page payloads and the modules that feed them**, not to the record.

---

## 9. SUCCESSOR ROWS — the `UNMEASURED` cells, MEASURED (`CANON-UNMEASURED`, 2026-10-13)

**r1, register `PREREG_canonmove_unmeasured.md` committed ALONE at `e4b0dae`.** ZERO TRIALS on
every row: each is a RE-MEASUREMENT of an already-registered construction on this universe (the
`S25` / `X7RECON` / `CORRECTED-FLOORS` class), every threshold INHERITED from the register that
set it, and every figure the **DEPLOYED flat-1/7 book**. **ADOPTS NOTHING; NO PUBLIC PAGE CHANGED
BY THIS LANE.** Full reasoning and controls: `HANDOFF_canon_unmeasured.md`.

**§0's weighting control passes at |dev| 0.000e+00 on 3 of 3 cells, gated on the count**, so every
row below is measured against the object this table describes. **§0's disjoint-grid caveat is
inherited unchanged: no move below is attributed to the universe alone.**

| the `UNMEASURED` cell | published | corrected | state |
|---|---|---|---|
| Deflated Sharpe, DEPLOYED book (§0 point 2) | 0.7863 at `N` 224 | **0.7208 at `N` 297** | **SURVIVES** |
| PBO, DEPLOYED book (§0 point 2) | 0.7333 | **—** | **UNMEASURABLE-BY-CONSTRUCTION** |
| `X1` A1 — top-decile alpha, half books | +0.07174 | **median +0.06046, 0 of 200 negative** | **SURVIVES** |
| `X1` A2 — long-short HAC *t*, half books | +2.6199 | **median +4.3727, 0 of 200 negative** | **SURVIVES** |
| *"400 half-universe books, not one negative"* | — | **RESTATES VERBATIM** | **SURVIVES** |
| `R1`'s net-of-cost specification (R1's OWN path) | +7.85%/yr *t* 5.16 (VOID panel) | **+4.06%/yr, NW *t* 3.01** | **SURVIVES** |
| `optionable_partition.N_PANEL_NAMES` | 2,531 | **9,645** | **RESTATEMENT** |
| `optionable_partition.N_OPTIONABLE_NAMES` | 619 | **630** | **RESTATEMENT** |
| the lede's *"roughly a quarter … has listed options"* | 24.46% | **6.53%** | **NO LONGER HOLDS** |
| `V6-B` M1 dip survival | 32.5% vs 43.4% | see §9.5 | see §9.5 |
| `S22`'s eight per-horizon `fixed_weights_null` floors | — | see §9.6 | see §9.6 |
| the live / forward Track Record | — | **—** | **UNMEASURED-BY-CONSTRUCTION** |

### 9.1 THE DEFLATED SHARPE — and §0 POINT 2 IS IMPRECISE ABOUT PBO

**The deployed book's Deflated Sharpe is 0.720824 at equity `N` = 297**, against the conventional
>0.95 (**fails**, as the published 0.7863 did) and the matched **non-adopting** placebo floor
**0.565519** over 84 draws (**clears**, as the published figure did). Same relationship to both
bars, so **SURVIVES**. The comparison is like-for-like on the BOOK: the published run's own
`cpcv.adopt` was **False**, so 0.7863 *is* the deployed book.

**IT IS 490× THE ADOPTED BOOK'S 0.001472**, which is what §0 point 2 exists to prevent anyone
pairing with deployed figures.

**AND MOST OF THE FALL IS THIS PROJECT'S OWN TRIAL COUNTER.** `sr0` is a function of `_trial_N()`.
Separated from banked numbers alone: the published book at `N` = 297 reads **0.746246** and the
corrected book at `N` = 224 reads **0.763053** — so of the 0.0655 fall, **~0.040 is `N` rising
224 → 297** and only 0.023–0.025 is the universe and grid.

**THE PRECISION CORRECTION.** §0 point 2 says `cpcv.pbo` *"describes the ADOPTED book"*. True of
the Deflated Sharpe; **imprecise of PBO**. `_pbo` never reads `adopt` or `recommend` — it scores
the **SELECTION STEP** over the eight candidates (its own `pbo_scope` says so), so the shipped
figure is the same number whether or not adoption happened. **The deployed book selects nothing,
so Bailey–López de Prado's PBO is not a statistic about it in either direction.** The
deployed-book analogue (the same rank arithmetic with the argmax replaced by the fixed scheme)
reads **1.0** at a median out-of-sample rank of 0.25 of eight — and the per-scheme control proves
it is a pure **RANK** statistic (0.0 for the three best schemes, 1.0 for the three worst), so it
**may never be rendered as a probability of overfitting** and has no calibrated floor.
**`/proof` should keep showing the deployed PBO as UNMEASURED, now with that reason beside it.**

**REACHABLE FROM THE NEXT CANONICAL RUN:** `cpcv.deployed_readings` is now computed and
PROJECTED (`SCHEMA_VERSION` 7 → 8, purely additive, registered in
`payload_schema.BLOCK_SPEC` so `M6`'s field-level guard carries it). The tracked artifact is
**not** re-generated here — that is the app fixer's, per §7.

### 9.2 `X1` — BOTH ARMS SURVIVE, AND A2 IS THE ARM THAT MOVED

Bars and constants IMPORTED from `PREREG_r4_x1_accounting_and_universe_split.md`, read through
its own `verdict_of`. Half-universe null at 200 draws, well centred (alpha median **+0.000863**,
long-short HAC *t* median **−0.0594**).

| | A1 alpha | A2 long-short HAC *t* |
|---|---|---|
| null p95 (the bar) | +0.013414 | +1.4661 |
| stable-key halves A / B | +0.054666 / +0.059699 | +4.3251 / +4.4646 |
| half books clearing (bar 0.80) | **1.000** | **1.000** |
| splits clearing both sides (bar 0.64) | **1.000** | **1.000** |
| median / min / max of 200 half books | +0.06046 / **+0.04189** / +0.07679 | +4.3727 / **+3.2940** / +5.7055 |
| negative half books | **0** | **0** |

**ON THE PUBLISHED UNIVERSE A2 CLEARED ONLY 93.0% OF HALF BOOKS AND 86.0% OF SPLITS**, which is
why the record had to call A1 the stronger claim. **Both are 100%/100% here** and A2's median
half-book *t* rises **+2.3617 → +4.3727**. A1's level is slightly lower (median +0.07233 →
+0.06046), which is the universe's own alpha falling rather than the split degrading.

**SO THE SENTENCE §1 FORBADE RESTATING NOW RESTATES VERBATIM** — 200 half books per arm × two
arms = 400 measurements, zero negative, and the worst still earns +4.19%/yr at *t* 3.29.

### 9.3 `R1`'s NET-OF-COST CELL — IT CLEARS, AND IT FAILS IF BOTH TRADE LEGS ARE CHARGED

**The NaN was a zero-date LEFT JOIN** against `X4`'s shipped strategy series, which is indexed on
X4's own 110-date grid. **AND THE PUBLISHED PANEL SHARES ZERO DATES WITH IT TOO**, so that cell
has been unmeasurable **since `B6`**, not since this move: the shipped +7.85%/yr (*t* 5.16) is
`FACTOR_ALPHA_RESULTS.json`'s 109-period VOID pre-B6 run.

**R1's arithmetic is NOT edited.** `--strategy-series` is an argument; a corrected series was
supplied, built by the shipped producer. The gross leg reproduces the landed
`+0.059397599064971024` at *t* `+4.453158903833538` at **dev 0.000e+00** on all three readings.

| reading | drag /yr | net intercept /yr | NW *t* | R1's bar (positive, *t* > 2.0) |
|---|---|---|---|---|
| **PRIMARY** — shipped composite | 1.8787% | **+4.0583%** | **+3.0094** | **CLEARS** |
| sensitivity — pre-`B7` legacy composite | 1.8298% | +4.1099% | +3.0420 | clears |
| **sensitivity — BOTH trade legs charged** | 3.6903% | **+2.2936%** | **+1.7084** | **DOES NOT CLEAR** |

**REPORTED, NOT FIXED:** `cost = (cost_bps/1e4) × turnover` charges the one-way cost on the
**entering** side only, while `turnover_and_costs` charges both legs — so R1's leg undercharges by
about 2× against this project's own cost model, **and the discrepancy crosses R1's bar.** R1's
registered formula is run as written; re-pointing it is a different register's business.

### 9.4 `P1S0` — THE NUMERATOR IS A CONSTANT, SO THE PAGE'S FRACTION IS WRONG BY 3.7×

`N_OPTIONABLE_NAMES` 619 → **630** (up 1.8%) while `N_PANEL_NAMES` went **3.8×**, because the
chain cache is a **targeted pull** of large, liquid names: 1,000 ticker directories on disk, 923
of them in the corrected panel. So the optionable share falls **24.46% → 6.53%**, 39 of 69 dates
carry a chain, and `optionable_partition.py`'s lede — *"Roughly a quarter of the research panel
has listed options"* — **is wrong by 3.7× and is the real change.** *One name in fifteen* is the
honest phrasing. The stamp moves **only with its figures**, as §6 instructed.

**AND ONE OBSERVATION, REPORTED WITH NO VERDICT AND ROUTED TO DON.** `P1S0` closed the
options-expression family on an early half that was **absent** (cumulative alpha −0.08% at H=252,
*t* 0.8352 at the H=63 power anchor). On the corrected panel **every early-half cell is positive**
at all three horizons in both partition modes (H=63 +7.40% at *t* 1.82, H=252 +14.81%, H=504
+5.28%), and the optionable subset beats the full panel over the same dates at every horizon.
**It carries NO verdict:** the per-horizon placebo floors were not re-run, the window is 39
post-2016 dates rather than 69, and re-opening the family is Don's and needs its own blind
register. **`P1S0-CONTROL`'s NULL is not re-opened.**

### 9.5 `V6-B` M1 — see `HANDOFF_canon_unmeasured.md` §4.2

`C1`'s gate aborted the earlier corrected attempt against the PUBLISHED literals on a panel its
own `C2` had just certified as canonical. It is now re-pointable (`--expect-record`, defaulting
to `REC` verbatim), and the corrected expectation is DERIVED rather than typed. Bars IMPORTED
from `PREREG_v6b_dip_survival.md` and never restated.

### 9.6 `S22`'s per-horizon floors — see `HANDOFF_canon_unmeasured.md` §4.3

200 draws × 8 horizons, the construction `S22` registered. **`MB21`'s caveat travels with any
figure read off them: `fixed_weights_null` permutes WITHIN each date, so it has no memory and is
a DIFFERENT, less conservative null than X7's — its percentiles may NEVER be compared with the
2.2837 family.** A shortfall is reported PARTIAL, never quoted as a floor.

### 9.7 WHAT §9 DOES NOT DO

* **It changes no public page and does not re-generate or swap the tracked artifact** (§7 still
  holds; the register's own void condition 4 repeats it).
* **It adopts nothing** and re-opens nothing: `P1S0`, `P1S0-CONTROL`, `V6-B` and `S22` keep their
  own verdicts, carried rather than re-decided.
* **It attributes no move to the universe alone** — §0's disjoint grids forbid it.
* **It does not re-run `X1`'s theme decisions or weight selection under the split**, which is a
  different question from generalisation across names.
