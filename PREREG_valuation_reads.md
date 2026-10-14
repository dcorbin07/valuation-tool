# PRE-REGISTRATION — `VALREADS` — the valuation page's new reads, tested forward

**Committed ALONE, markdown only, zero `.py`, BEFORE THE FIRST ROW EXISTS.** This file must be a
strict git ancestor of the recorder, of the first recorded row and of every commit that computes a
statistic on it. If it is not, the item is VOID.

**This register reads no verdict and adopts nothing.** It fixes, today, what will be measured, on
which rows, against which bar, on which date, and — the part this project has learned to insist on
— **what the design can and cannot see on each of those dates.**

---

## 0. Why a forward record is the only route, and why today's archive is not it

The valuation page's Buy / Hold / Reduce labels were never tested against returns and are now gone
(`DECISIONS.md`, "The valuation page", 2026-10-13). Their replacements — business quality, price vs
our model, what the price assumes, and the DCF warning — will not be tested either unless they are
recorded as they are served.

**They cannot be rebuilt for past dates, and that is measured rather than assumed.** `V6`
established that the live sub-scores are not computable point-in-time: quality needs a WACC, and
`S23` measured that path fetching **live Yahoo prices to value 1999**. So a backfill would not be a
reconstruction of what the page said; it would be a different number wearing an old date.

**And the archive this project already has cannot answer it.** `valuation/edge/archive.py`
(`archive_scan`) keeps **the top 100 hot names a day and none of these reads** — no business
quality, no price-vs-model, no implied growth, no warning flag. NVDA sits at hot rank 1,262, so the
archive is silent about the single name item 52's own handoff uses as its worked example.

**`VALREADS` is therefore a recording decision, and this file is the test that recording is for.**

---

## 1. The reads under test

Five, all from item 52 and all served on the valuation page today:

| id | read | source | type | DECLARED SIGN |
|---|---|---|---|---|
| `R1-BQ` | `business_quality_score`, 0–100 | `scoring.business_quality` | continuous | **POSITIVE** — a better business earns more |
| `R2-PVM` | `price_vs_model_pct` = `price / base_fv − 1` | `scoring.price_vs_model`'s own numeric | continuous | **NEGATIVE** — cheaper against the model earns more |
| `R3-PIG` | `price_implied_growth`, the reverse-DCF rate | `price_assumes.price_assumes` → `implied` | continuous | **NEGATIVE** — a lower bar to clear earns more |
| `R4-GAP` | `story_gap_pp` = implied growth − the business's growth, in pp | `price_assumes.story_gap_pp` | continuous | **NEGATIVE** — a wider gap is a higher bar |
| `R5-WARN` | the DCF warning flag, and which rule fired | `price_assumes.dcf_warning` → `triggers` | **binary** | **NEGATIVE** — a warned name earns less |

**Every sign is declared here, before any row exists.** A two-sided reading is forbidden: this
project has three times recorded a published sign failing to reproduce (`O7`, `U2`, `MA31`), and a
sign chosen after the fact is not a sign.

**`R1-BQ` IS NOT INDEPENDENT OF THE SUB-SCORES AND THE REGISTER SAYS SO FIRST.**
`business_quality` is a weighted mean of the four `BUSINESS_SUBSCORES` (`quality`, `growth`,
`health`, `momentum`). So a positive `R1-BQ` would be a finding about **this particular
aggregation and the 0–100 band labels the page renders**, never a new finding that quality
predicts returns — which this project has already measured on the panel (`quality` theme IC *t*
+3.10). The five sub-scores are **recorded** (§3) and are **NOT registered arms**; they exist here
as the power control of §6.

**`R5-WARN` IS A BINARY AND IS SCORED AS A MEAN DIFFERENCE, NOT AN IC.** A rank IC on a flag with
two values is a point-biserial correlation whose magnitude is a function of the flag's base rate,
so it would not be comparable with the other four cells. Its statistic is the per-date difference in
mean forward return between warned and unwarned names, and its bar is its own permutation p95 on
that statistic. **Its trigger is recorded per name** (`hypergrowth`, `cash_burning`, `growth_led`,
`low_reliability`, `story`), because `STORY_GAP_PP = 15.0` is, in item 52's own words, *"a
disclosure threshold and is calibrated against nothing"* — so which rule fired is the only way a
successor can tell a real signal from one rule carrying everything. **No per-rule arm is registered
and none may be read**; sub-dividing a null until a cell clears is the mining this file exists to
prevent.

---

## 2. The statistic

For each read and each horizon: the **per-date cross-sectional Spearman rank IC** of the read
against the forward total return over 3, 6 and 12 months, then the mean of those per-date ICs with a
Newey–West standard error at the lag the overlap implies.

* **Spearman, not Pearson, fixed here.** `MA56` is this project's own record of a register whose
  verdict reversed on that choice (Spearman +0.07034, Pearson −0.82793).
* **The forward return is the total return**, from the same price series the recorder stamps,
  dividend-adjusted. `R8`'s correction applies: the panel's `close` is already `closeadj`.
* **A name that leaves the population mid-window keeps its realised return to its last available
  close and is NOT dropped**, because dropping it selects on survival. **A name that leaves because
  it stopped trading has a TERMINAL value, and a name that leaves because the population moved is
  CENSORED and is excluded from that horizon** — `E-5`'s distinction, which cost that register a
  silent deletion of 16 crashes before it was separated.
* **Overlap is corrected, not ignored.** A 3-month forward return recorded weekly is the same
  return thirteen times over. The independent count is
  `power_gate.available_independent_n_nonoverlapping(weeks, 4.33 × horizon_months)`, and the NW lag
  is `ceil(4.33 × horizon_months) − 1`.
* `R5-WARN`'s statistic is the per-date mean-return difference, same NW treatment.

---

## 3. The population, and it is FIXED HERE

**THE RULE, fixed before any row and never to be chosen afterwards:** every name in the union of

* **(a)** the rows the **published hot list** serves — `GET /api/hotstocks?top=500`, public and
  tokenless; and
* **(b)** every constituent of the **published Valquo Index** — `GET /api/valquo-index`, likewise.

**Measured today, before the rule was written down** (`data/free_analysis/VALREADS_COST.json`):
the hot route **caps at 500 rows whatever `top` asks for**, the Index carries **86** positions, and
**only 44 of those 86 are inside the hot 500 — 42 are outside.** Union **542**.

**That measurement is why the rule is a union rather than "the hot list".** A hot-list-only
population would omit half of the product's own book — the one population a forward record of the
valuation page's reads must certainly contain.

**THE COST THAT FORCES A POPULATION RATHER THAN "EVERY NAME IN THE SCAN", measured first as the
task required.** One `pipeline.value_ticker` costs **1.83 s** per name over a 12-name paced probe
(median 1.44 s, max 4.25 s; a second 6-name pass read 2.28 s), at **one company fetch per name**
and no options chain, no AI call and no forward return. At that pace the union is **≈ 34 minutes**
and the scan's full ~1,500-name universe would be **≈ 83 minutes**, against the hot scan's existing
`timeout-minutes: 90`. **So the union is affordable weekly and the full universe is not, on a free
runner, beside a job that already needs most of that budget.**

**THE CANARY RULE TRAVELS WITH THAT FIGURE.** The live feed's per-IP quota **does not raise when
exhausted — it silently degrades `CompanyData`** (measured 2026-08-07: 302 of 403 names arrived with
`beta=None`, the tell being many names reporting one identical WACC as it collapses to pure cost of
debt). A degraded run is **fast and wrong in the flattering direction**. The recorder therefore
values one known name first and **refuses to record the week at all** if that canary comes back
degraded — a missing week is a fact; a week of blank reads recorded as reads is a lie.

**What may and may not move.** The RULE is frozen. The realised **count** may move — the hot route's
cap is a server-side constant this lane does not own, and the Index rebalances — so the recorder
stamps `n_hot`, `n_index`, `n_index_outside_hot` and `n_population` **on every row's header**, and a
cap change is therefore visible in the record rather than silent. **Changing the rule voids the
item.**

---

## 4. The read schedule — each cell is read EXACTLY ONCE, and not early

`INCEPTION` is the date of the recorder's **first** row and is stamped in the record itself. Every
date below is **DERIVED from it and must never be quoted from a document** — this project has reset
a five-year clock three times in four days and recorded a hard-coded vintage date rotting within
days (`PT-GAPDUE`).

| read date | cells read | trials charged |
|---|---|---|
| `INCEPTION + 1,826 days` (5 years) | all five reads at the **3-month** horizon — **5 cells** | **5 equity** |
| `INCEPTION + 3,653 days` (10 years) | all five reads at the **6-** and **12-month** horizons — **10 cells** | **10 equity** |

**Fifteen cells, fifteen equity trials, each cell read once.** Nothing is read before its own date;
nothing is re-read after it. A cell read early, or twice, VOIDS the item — `S3-I1`'s own lesson is
that a peek rule nobody can check is an honour system, so the verdict script must refuse on a date
earlier than the derived one and must record the read.

**Why the horizons are split across two dates rather than all read at five years:** because at five
years the 6- and 12-month cells cannot resolve, and §6 says so with numbers. Reading them then and
calling the result a null would be reporting a design's blindness as a finding.

**The trial charge is at the read, not now.** `MB1-SEL`'s rule: a register that never reads a
verdict charges nothing. **Overstating is the safe direction** (`MA6`), so all fifteen are charged
in full even though five reads × three horizons on one record are not fifteen independent searches.

---

## 5. The bars, and how each is calibrated

A cell **CLEARS** only if **all four** of the following hold. Any other outcome is a **NULL**.

1. **Its own within-date permutation p95.** At verdict time, shuffle that read **within each
   recorded date**, 500 draws, preserving each date's own distribution and missingness pattern
   exactly, and recompute the statistic. The bar is the 95th percentile of the draws, **one-sided in
   the declared direction**. This is `V6`'s, `E-5`'s and `O14`'s construction.
   * **ITS LIMIT SHIPS WITH IT.** A within-date permutation has **no memory** — `MB21` measured
     `fixed_weights_null`'s per-name rank autocorrelation at −0.0016 against a real composite's
     0.5677 — so it **cannot** price the Boudoukh–Richardson–Whitelaw overlap artefact that
     overlapping windows carry. The NW lag of §2 is the only correction for that, and it is an
     imperfect one. **A cell clearing by a hair at a long horizon is not safe**, and `MB21`'s
     measured shortfall at overlapping horizons (+0.10 to +0.25 of a *t*) is the scale of the
     problem.
   * **No floor from this project's existing table may be borrowed.** `2.2837`, `2.0540`, `2.7072`
     and `19.667%` are calibrated on the **full-universe quarterly decile book**, and this is a
     542-name weekly record of different statistics. `X7RECON` and `MA19` are the record of what
     borrowing a floor across regimes costs.
2. **Benjamini–Hochberg across the cells read on that date, q = 0.10.** Five cells at the first
   read, ten at the second. `statistics.benjamini_hochberg` is the one definition
   (`R4`'s consolidation) and no second copy may be written.
   * **ITS LIMIT SHIPS WITH IT TOO: these cells are not independent.** `R1-BQ` is built from the
     sub-scores; `R3-PIG` and `R4-GAP` share a term by construction (`R4 = R3 − business growth`);
     and the three horizons of one read are the same signal measured over nested windows.
     `SELRULE` measured 16 co-moving countries to be worth **2 to 4** independent draws, so BH is
     being fed correlated tests and the effective number of cells is **nearer five than fifteen**.
3. **The both-halves rule.** Split that read's usable span at its own median recorded date; the
   full span **and both halves** must clear their own permutation p95, **with the same sign
   throughout.** Halves disagreeing in sign is a NULL in either direction — it is the most repeated
   pattern in this project's record (session 7's LOO, `S17`, `V6`, `S8`/`S9`, `S11`/`S12`,
   `O21-D2`, `E-2`, `D6`, `MB20`: ten instruments).
   * **ITS COST IS STATED IN ADVANCE.** At the first read a half carries `n_eff ≈ 9.5`, so its own
     80%-power MDE is about **0.096** — larger than the effect being hunted. **A cell can therefore
     clear the full span and fail a half, and that is a NULL and not a near-miss** (`RUN_RULES` A6).
4. **The HLZ hurdle is reported beside every cell, and is NOT a gate here.** `√(2·ln N)` at the
   then-current equity `N`, derived at read time from `RESEARCH_LOG.md` and never quoted from a
   document. **Today it reads 3.3745 at equity `N` = 297.** It is reported rather than gated for
   `R4`'s own measured reason: HLZ prices the **best of N draws**, and these five reads are what the
   page already serves — they were not selected out of this record. **§6 states what gating on it
   would cost, so a successor cannot claim the choice was made for convenience.**

---

## 6. POWER — what this design can and cannot see, stated before it runs

`RUN_RULES` PART A rule 11. Derived with `valuation/edge/power_gate.py` and never retyped
(`MA5`), from a **MEASURED** dispersion rather than an assumed one:
`scripts/valreads_power.py`, `data/free_analysis/VALREADS_POWER.json`.

**THE DISPERSION IS MEASURED.** Per-date Spearman IC against `fwd_ret` on this project's own
corrected 9,645-name panel, 69 dates: `quality` mean **+0.0695** at sd **0.0872**, `growth`
+0.0110 / 0.0592, `momentum` +0.0417 / 0.1302, `value` +0.0547 / 0.1116, `size` −0.0703 / 0.0941.
Re-scaled to a 542-name cross-section — `sd² = true_var + 1/(N−1)`, so the N-independent part is
carried over and the sampling term is added back at the recorder's own size — the five give
**0.0715 to 0.1362**, and the **midpoint 0.1038** is used below.

**THE EFFECT WORTH DETECTING IS THIS PROJECT'S OWN BEST MEASURED READ, not one chosen to flatter
the design: `quality`'s IC of +0.0695**, the largest of the five. A design that cannot see it
cannot see anything this project has measured.

**At the first read (5 years), against the placeholder bar 2.0:**

> MDE at |t| > 2.0000: detection threshold **0.0464** (50% power); **0.0659** at 80% power.
> **Power against a quality-like read of 0.0695 is 84.0%.**

**At the same read, if the HLZ hurdle were gated on instead:**

> MDE at |t| > 3.3745 (N = 297): detection threshold **0.0783** (50% power); **0.0978** at 80%
> power. **Power against 0.0695 is 35.2%.**

**YEARS OF RECORDING BEFORE A HORIZON REACHES 80% POWER against a quality-like read:**

| horizon | at the placebo-class bar 2.0 | at X7's theme-IC floor 2.7072 | at the HLZ hurdle 3.3745 |
|---|---|---|---|
| 3 months | **4.6 years** | 7.1 years | 10.0 years |
| 6 months | **9.1 years** | 14.1 years | 19.9 years |
| 12 months | **18.1 years** | 28.2 years | 39.7 years |

**THE HONEST STATEMENT, which the task asked for and which is a finding rather than a reason to
skip:**

* **The 3-month cells are powered at the first read and only just** — 4.6 years of recording to
  reach 80%, against a read at 5.0 years. There is no slack; a year of missed weeks pushes it out.
* **The 6-month cells are not powered until about year 9 and are read at year 10.**
* **THE 12-MONTH CELLS DO NOT REACH 80% POWER UNTIL ABOUT 2044, AND NOT UNTIL ABOUT 2066 IF THE
  HLZ HURDLE IS GATED ON.** They are read at year 10 at roughly **55%** power and the register says
  so now. **A 12-month null in 2036 will mean "this design could not see it", and it may not be
  reported as anything stronger.**
* **If the real effect is smaller than a quality-like 0.0695 — and four of the five panel reads
  are — every date above moves out, quadratically.** At an IC of 0.035 the 3-month cell needs
  roughly **18 years**.

**So: it is unlikely that anything but the 3-month horizon resolves before about 2036, and the
12-month horizon is unlikely to resolve this side of 2044.** Recording is still worth doing, for
the reason §0 gives: the alternative is not a cheaper test, it is **no test, ever**, because these
reads cannot be rebuilt backwards.

---

## 7. What a NULL means, and what it does not

**A NULL means "no effect this design could separate from noise at this resolution", and nothing
stronger.** Every null reported under this register **must travel with its own measured MDE** —
`V6`'s and `S19`'s rule, and `MB8`'s refinement that an `se` may never be borrowed from another
construction. A null quoted without its MDE is a void condition of this register.

**A NULL IS NOT:**

* evidence that the valuation page's reads are worthless. They are **disclosures** — "priced 56%
  above our base value" is a statement about this model's own arithmetic, and it is **true or false
  on its own terms** regardless of whether it sorts returns;
* a reason to remove them, re-word them, or re-rank anything;
* a finding about business quality, cheapness or reverse-DCF generally. It is a finding about
  **these five constructions, on this population, at this resolution.**

**A CLEAR is not an adoption either.** Nothing in this register ships a change to the valuation
page, the hot list, the Index or any number a user receives. An adoption would be a construction
change and a **vintage event** — Don's call, with its own register.

---

## 8. Void conditions

The item is VOID, and its cells carry no verdict, if any of these happens:

1. **The population rule of §3 changes** after recording starts — including "measure on the subset
   that has full coverage" after seeing which subset that is.
2. **Any row is backfilled, edited or deleted.** The record is append-only. A missing week is
   recorded as missing.
3. **A cell is read before its derived date, or read twice**, or a horizon is added, or a bar is
   relaxed after a cell has been seen to fail it (`W-28`'s §6 rule, and its own register's kill).
4. **A forward return is read anywhere in the recorder.** The recorder must be provably incapable
   of it — pinned by test, not by inspection (§9).
5. **A per-rule arm of `R5-WARN` is read**, or any cell is sub-divided by sector, regime, cap tier
   or reliability until something clears. Those are new hypotheses and need their own register.
6. **A statistic other than §2's is substituted** after the data exists — including swapping
   Spearman for Pearson, the mean for the median, or the IC for a decile spread.
7. **A floor is borrowed** from this project's existing calibrated table (§5.1).

---

## 9. Day-one self-check — the recorder must demonstrate these before it records anything

1. **A row round-trips unchanged** — written, read back through the record's own reader, and
   compared field by field.
2. **A refused valuation records as REFUSED, with its reason, and never as a blank.** `archive.py`
   is this project's own record of the opposite: it stored `fair_value` but neither the refusal flag
   nor its reason, so a permanent archive could not tell *"we declined to value this"* from *"we
   never tried"*.
3. **Nothing in the recorder reads a forward return** — asserted over the **syntax tree**, not by
   grep, because a docstring describing the rule contains the words the rule forbids
   (`MA49`/`MB1`: the substring-ban family, which has fired against a correct tree at least six
   times in this project).
4. **The append-only guarantee holds at the byte level** — the file on disk is an exact prefix of
   itself plus the new rows, which is the check `S3-I1`'s `append_only.py` already implements and
   which is **delegated to, never re-implemented** (`B7`).
5. **The canary refusal fires** — a degraded fetch must produce a recorded refusal for the week and
   not a week of blank reads.
6. **The self-check is not vacuous** — each of the above must be shown to FAIL against a
   deliberately broken input, or it is not a check (`MB21`'s `C1`, which scored a perfect 0.000e+00
   by comparing nothing).

---

## 10. Expectations, stated now so they can be scored against

Written before any row exists. They are forecasts, not findings, and they carry no weight in any
verdict.

1. **`R2-PVM` is the most likely of the five to clear**, at 55/45. It is the closest to a
   conventional value signal, and `value` reads +0.0547 on the panel.
2. **`R1-BQ` clears at 40/60** — and if it does, §1's caveat binds: it will be a finding about the
   aggregation, not about quality.
3. **`R4-GAP` will be measurable on far fewer rows than the other four**, at 80/20, because it
   needs both an implied growth and a business growth and `story_gap_pp` returns `None` rather than
   0.0 when either is absent. (`price_assumes` returns `available: False` on the same condition.)
4. **`R5-WARN` will be dominated by one trigger**, at 70/30, and on item 52's own worked example
   TSLA is caught by the story rule **alone**.
5. **At least one cell's halves will disagree in sign**, at 85/15 — ten instruments have.
6. **The 12-month cells will be reported UNDERPOWERED rather than NULL or CLEAR**, at 75/25.
7. **The realised population will not be exactly 542 at the first read**, at 90/10 — the Index
   rebalances and the hot cap is not this lane's constant.

---

## 11. Not done, named so it is not mistaken for done

* **No verdict is read here and nothing is adopted.** No cell has a value, because no row exists.
* **No change to the valuation page, the hot list, the Index or any public surface.** This lane
  does not change public copy; any figure a successor finds goes to the app lane.
* **The five sub-scores are recorded and are NOT registered arms.** `MA58`'s and `D6`'s power
  control is their only role here.
* **No per-rule arm, no sector cut, no regime cut, no cap-tier cut.** §8.5.
* **`V6` is not re-opened**, `S25-REPAIR` is not wired, and nothing here touches the live scoring
  path.
* **`STORY_GAP_PP = 15.0` is not calibrated by this register and is not calibrated anywhere.** It
  is a disclosure threshold; recording which rule fired is what would let a successor calibrate it,
  and **that successor is not proposed.**

---

## AMENDMENT 1 — made 2026-10-13, BEFORE THE FIRST ROW EXISTS AND BEFORE ANY OUTCOME

**`R3-PIG` and `R4-GAP` are scoped to NON-FINANCIAL names. A financial's implied figure is a
DIFFERENT QUANTITY and is recorded in its own column, carrying no registered arm.**

**Why, and it is a defect in this register caught by building the recorder rather than by reading
it.** §1 sources `R3-PIG` from `price_assumes.price_assumes` → `implied`. Measured in the source:
when `is_financial` is true that function takes a deliberate separate branch — *"a bank's value is
not a discounted free-cash-flow stream, so 'what growth does the price assume' is the wrong
question and the honest one is what return on equity it has to earn"* — and returns an **implied
return on equity** under the same key. So the register as written would have put an ROE and a
growth rate in one column, and any rank IC computed on it would have been mixing two quantities.
**That is the wrong-object family this project has recorded at least six times** (`MB18`'s column
literally called `gap`, `D6`'s `long_short_tstat_hac`, `E-5`'s stranded `MA28_CARD` path, `W-1`'s
`W1_FLOORS.json`, `U2`'s `term_slope_60_30`, `MA47`'s ticker count read as ticker identity) — and
it computes cleanly, raises nothing, and answers a different question.

**It is not a rare branch, so scoping it is not cosmetic.** The recorder's own smoke test found a
financial among the first four hot names (`ABCB`, regime `financial`, blend method *"justified P/B
from ROE"*, and `price_implied_growth` correctly blank), and §3's population deliberately includes
the Index, which holds banks.

**What changes and what does not.**

* `R3-PIG` and `R4-GAP` are measured on rows with `regime != "financial"`. The register's power
  statement (§6) is therefore **optimistic by the financial share** on those two reads, which is
  **NOT yet measured** and will be reported at the first read from the record's own `regime`
  column. The direction is named rather than estimated: a smaller cross-section raises `sd(IC)`
  through the `1/(N−1)` term, so both cells resolve later than §6 says, not sooner.
* **The implied ROE is recorded** as its own column (`price_implied_roe`, with `book_roe` beside
  it) so a successor can register it. **No arm is registered on it here and none may be read** —
  that would be a sixth read chosen after the data existed.
* **`R1-BQ`, `R2-PVM` and `R5-WARN` are unchanged** and still cover every name, financial or not.
* **The cell count, the read dates and the trial charge are unchanged** at fifteen cells and
  fifteen equity trials. This is a scoping correction, not a new hypothesis.

**Why this is an amendment rather than a silent fix.** It predates the first row, so no outcome
could have informed it — which is the only condition under which this project permits one (`W-1`'s
Amendment 1 and `W-28`'s Amendments 1 and 2 were all made before any outcome existed). The
original §1 is left standing above, unedited, so a reader can see what was corrected rather than
having to diff for it.
