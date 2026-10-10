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

