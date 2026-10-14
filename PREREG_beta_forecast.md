# PRE-REGISTRATION — `BETA-FORECAST` — which beta best forecasts a name's realised beta

**Committed ALONE, markdown only, zero `.py`.** A strict git ancestor of every commit that computes
a loss. If it is not, the item is VOID.

Don's queued research, `DECISIONS.md` 2026-10-13: *"a test of an adjusted beta against the vendor's
raw beta before any change to the valuation engine."* Item 53 measured that the discount rate
dominates some fair values — **NVDA $145.67 at its vendor beta of 2.22 against $230.65 at beta
1.0, on a $226 price** — and KO's 0.32 flatters it the other way.

**ADOPTS NOTHING.** A winner goes to Don with the two consequences §9 states.

---

## 1. WHAT IS NEW, AND WHAT IS NOT RE-OPENED

`wacc.py` carries `BETA_SHRINK = None` with its own note: *"Measured and REJECTED in Part 2 of
`HANDOFF_live_data_bugs.md` — it breached the do-no-harm bound at 2.491% against a 2% ceiling."*

**THAT REJECTION STANDS AND IS NOT RE-OPENED.** It answered *how much do fair values MOVE* — a
do-no-harm bound, on 128 names, resolving **0 of 6** decisive names. **This register asks a
different question that has never been tested here: is the raw beta the best available FORECAST of
a name's future beta?** That is the question Blume (1971) answers, and **a candidate can fail a
do-no-harm bound and still be the better estimator** — those are different claims and the record
should hold both rather than letting one stand in for the other.

---

## 2. THE CANDIDATES

| id | candidate | definition |
|---|---|---|
| **(a)** `b_raw` | the vendor's own construction | `cov(r, m) / var(m)` over the trailing **60 monthly** returns, market **SPY**, min **36** observations |
| **(b)** `b_blume` | Blume (1971) / Bloomberg "adjusted beta" | `0.67 × b_raw + 0.33 × 1.0` |
| **(c)** `b_sector` | industry median | the **median `b_raw` within the name's POINT-IN-TIME sector** at that formation month, min **5** names |

**THE ESTIMATOR IS THE SHIPPED ONE'S CONVENTION, NOT A NEW ONE.** `valuation/data/beta.py`'s own
docstring records why that window: it is *"the one validated in `HANDOFF_live_data_bugs.md` §2
against the vendor on control names"*, reproducing the vendor's column to a worst absolute
difference of **0.036** (JPM) — and a **one-year DAILY** window was tried first and is WRONG,
returning **KO −0.286 and XOM −0.484**. The 0.67 weight and the 1.0 target are `wacc.py`'s own.

**THERE IS NO HISTORICAL VENDOR BETA, SO (a) IS RECONSTRUCTED, AND THAT IS DECLARED RATHER THAN
GLOSSED.** The vendor field is a live quote with no history. The substitution is licensed by the
0.036 agreement above, not assumed.

**(c) USES `S25`'s DATED GICS MAP AND NEVER THE PANEL'S `sector` COLUMN**, because that column is
**TODAY's** classification — `S25` measured it and `S25-REPAIR` measured the cost (the fair value
moves on **every** row it touches and the valuation regime flips on **57%**). Using it in a
FORECASTING contest would hand the candidate under test knowledge of the future. The dated map
**refuses** rather than carrying a lapsed classification forward, and a refusal is recorded
`NOT_COVERED` rather than silently becoming a sector.

---

## 3. THE REALISED BETA, AND WHERE A LOOK-AHEAD WOULD LIVE

`b_real` is the same `cov/var` over the **24 months STRICTLY AFTER** the formation month, min
**20** observations. The two windows are produced by one function and
`tests/test_beta_forecast.py` asserts their intersection is **empty** — an off-by-one there is the
only way this design could leak.

**NO FORWARD RETURN IS READ ANYWHERE IN THIS ITEM.** A realised beta is a covariance with the
market; it is not a return anything is scored against, and no cell here is a performance claim.
Worth stating because every other register in this record scores a return.

---

## 4. THE POPULATION — AND THE FULL UNIVERSE IS MEASURED TO BE USELESS FOR THIS QUESTION

**Measured before this register was written** (`scripts/beta_forecast_contest.py --census`;
`data/free_analysis/BETA_FORECAST_CENSUS.json`, `BETA_FORECAST_CELLS.pkl`), 88 quarterly formation
months **2002-12 → 2024-09**:

| population | cells | tickers | months | sd of `b_real` | corr(`b_raw`, `b_real`) |
|---|---|---|---|---|---|
| full corrected universe | 307,286 | 7,222 | 88 | **6.348** | **0.0221** |
| **`cap ≥ $10B` (PRIMARY)** | **31,682** | **1,078** | **63** | **0.592** | **0.4201** |
| `cap ≥ $2B` (sensitivity) | 79,773 | 2,785 | 63 | 0.695 | 0.3645 |

**A BETA-FORECASTING CONTEST ON THE FULL CORRECTED UNIVERSE MEASURES NOTHING, AND THAT IS MEASURED
RATHER THAN ARGUED.** A realised 24-month beta with an sd of **6.35** and a correlation of
**0.0221** against its own trailing value is noise: microcap monthly returns are mostly
illiquidity, and the corrected universe carries **63.3% of weight under $300M**. On the `$10B`
tier the same estimator forecasts at **0.42** against a realised sd of **0.59** — a sensible
relationship.

**SO THE PRIMARY POPULATION IS THE INCUMBENT'S OWN `cap ≥ $10B` TIER**, at the most recent PRIOR
quarterly observation, and it is the right governing population for a second reason: **a fair value
only matters for a name the product values.** The full universe is **reported beside it** as the
measured reason the tier governs, and `cap ≥ $2B` is a declared sensitivity for robustness to the
threshold. The tier is an absolute market-cap **THRESHOLD**, not a rank, so `INDEX-CHOICE-ARM4`'s
ban does not apply (a $10bn company is $10bn in any subsample).

**DISCLOSED, BECAUSE I HAVE SEEN IT:** the correlation figures above involve `b_real` and were read
before this register was committed. They are a **dispersion/association** fact and **no loss was
computed** — the mean of the paired error difference, which IS the verdict, was deliberately not
read, and the SD alone was taken for §7's power statement. Seeing a near-zero correlation on the
full universe is what moved the primary to the tier; it changes **no bar**, because every bar below
is a comparison BETWEEN candidates and is unaffected by how well any of them does.

**SECTOR COVERAGE, and it independently reproduces `S25`:** on the `$10B` tier the dated map covers
**94.8%** of cells (30,033 of 31,682 over 1,016 names) — **the same 94.8% `S25` published** — while
on the full universe it covers **37.94%**. That is the confirmation that S25's figure was always a
megacap-tier number. **So (c) is scored on the tier's sector-covered intersection with the
coverage reported, and (a) vs (b) is scored on ALL tier cells**, since both are defined everywhere;
scoring three candidates on three different populations would make the comparison meaningless
(`S10`'s failure mode).

**BOTH HALVES**, split at the tier's median formation month, boundary embargoed.

---

## 5. THE LOSS

* **PRIMARY: mean ABSOLUTE error**, `|b_candidate − b_real|`. Absolute rather than squared because
  the realised beta has fat tails even inside the tier, and an RMSE on this object is a statement
  about a handful of names.
* **SECONDARY, declared and carrying no verdict: RMSE.** Reported so a reader can see whether the
  two agree; a disagreement is itself the finding, as `DC-1` established for two return
  definitions.
* **The comparison is PAIRED per cell**: `d = |e_candidate| − |e_raw|`, so a negative `d` means the
  candidate is closer. A paired contrast on identical rows removes everything that differs between
  names and dates — the same reasoning `MB8` used, and the reason its paired se was 8× smaller
  than `V2G`'s.

---

## 6. THE BARS — a candidate BEATS the raw beta only if ALL FOUR hold

* **B1 — DIRECTION.** Mean `d < 0` (the candidate is closer on average).
* **B2 — INFERENCE.** `|t| > 2.0` on the mean `d` under standard errors clustered on the formation
  **MONTH** and on the **TICKER**, **clearing required under BOTH**. A 60-month trailing window
  moved one quarter is almost the same window, so the month is a real cluster; a name appears at up
  to 63 formation months, so the ticker is too. **LABELLED UNCALIBRATED** (`V2G`, `R1-VAR`): no X7
  or `CORRECTED-FLOORS` figure transfers to a paired beta-forecast error, and none is quoted.
* **B3 — BOTH HALVES**, same sign, each clearing B1 and B2 on its own.
* **B4 — MATERIALITY, DERIVED FROM THE FAIR VALUE RATHER THAN CHOSEN.** `|mean d|` must exceed
  **0.05 beta units**. Derivation, from item 53's own measurement: NVDA's base value moved
  **$145.67 → $230.65** for a beta change of **2.22 → 1.00**, i.e. **+58.3% of fair value per 1.22
  of beta ≈ 0.478% per 0.01**. So **0.05 beta units ≈ 2.4% of fair value** — the same order as the
  **2%** do-no-harm ceiling the prior Blume test breached at 2.491%, which is what makes the two
  results comparable rather than two different scales.

**Anything else is a NULL** (`RUN_RULES` A6: ambiguous against a pre-committed threshold is a null,
not a judgement call).

---

## 7. POWER — stated before the loss is computed

From the tier's own measured SD of the paired absolute-error difference — **0.15316** on 31,682
cells, 63 month clusters, 1,078 ticker clusters — via `power_gate`, never retyped:

| clustering | clusters | worst-case se | **MDE80** |
|---|---|---|---|
| formation month | 63 | 0.01930 | **0.0548** beta units |
| ticker | 1,078 | 0.00466 | **0.0133** beta units |

**THE MATERIALITY FLOOR SITS AT 0.91× THE WORST-CASE MONTH-CLUSTERED MDE80, WHICH IS A KNIFE EDGE
AND IS SAID SO NOW.** The design sees a 0.05-beta improvement comfortably under ticker clustering
(3.8×) and only **marginally** under month clustering. **So a result at or near the floor is at the
edge of what this design can resolve, and B2's both-clusterings requirement is what stops that
being read as a clean pass.** The cluster inflation is `sqrt(n/G)` — the worst case of perfect
within-cluster correlation — so the realised se will be smaller and this is the conservative
direction; the verdict travels with the contest's OWN measured se (`MB8`: never borrow one).

**The floor is NOT set to what is detectable.** `R1-VAR` is the precedent in the other direction: a
*detection* threshold used as a *preference* threshold is a category error, and so is the reverse.
0.05 comes from the fair value.

---

## 8. Trials

**TWO EQUITY TRIALS**: (b) against (a), and (c) against (a). The `cap ≥ $2B` sensitivity, the RMSE
secondary and the full-universe reading carry **no verdict** and are **not** charged — they are
declared here so none can be promoted after the fact. Charged to **equity** because the fair values
a winner would move are equity claims, and overstating is the safe direction (`MA6`).

---

## 9. IF A CANDIDATE WINS — the two consequences that must be stated with it

**ADOPTS NOTHING. A winner goes to Don**, and under `DECISIONS.md` 2026-10-06 any candidate is
quoted at **half its backtested size** (McLean-Pontiff). Two consequences travel with it:

1. **IT CHANGES EVERY PUBLISHED FAIR VALUE.** Beta enters the cost of equity for every DCF the
   product shows, so this is a construction change with the blast radius of the whole valuation
   page — and therefore **a vintage event**, Don's call and nobody else's.
2. **`VALREADS` RECORDS THE VALUATION PAGE'S READS AS COMPUTED, SO A MID-RECORD CHANGE NEEDS A
   DATED AMENDMENT IN THAT REGISTER BEFORE IT SHIPS.** `PREREG_valuation_reads.md` began a weekly
   append-only record of `price_vs_model`, `price_implied_growth` and the rest on the explicit
   basis that the reads are recorded *as served*. Changing the beta changes `base_value` and
   therefore `price_vs_model_pct` for every name, so the record would contain two incomparable
   regimes with nothing saying where the seam is. That register's §8.1 makes an unannounced
   population or construction change a **void condition**; the amendment must be dated, committed
   alone, and must name the first recorded week scored under the new beta.

---

## 10. Void conditions

1. **Any bar changed after a candidate has been seen to fail it** (`W-28`: raise, never lower).
2. **The primary population changed** after the loss is computed, or the `$2B` sensitivity promoted
   to primary.
3. **RMSE quoted as the verdict**, or one loss quoted without the other.
4. **A candidate scored on a different population from the one it is compared against** (§4).
5. **A forward RETURN read anywhere in the item**, or the two beta windows made to overlap.
6. **The prior Blume rejection re-opened or restated** — §1 keeps it standing; this register adds a
   second, different measurement beside it.
7. **A winner shipped without the two consequences of §9**, or without a dated amendment to
   `PREREG_valuation_reads.md`.

---

## 11. Expectations, stated now

1. **Blume BEATS raw on direction (B1)**, at 80/20 — shrinking a noisy estimator toward the mean of
   its own distribution is the oldest result in this corner of the literature.
2. **Blume FAILS B4's materiality floor of 0.05**, at 60/40. Its whole adjustment is
   `0.33 × (1 − b_raw)`, and the tier's betas cluster near 1.0, so the average move is small.
3. **The sector median LOSES to raw**, at 75/25: it throws away every name-specific fact.
4. **The two losses agree on the ordering**, at 70/30.
5. **The halves agree in sign**, at 70/30.
6. **The overall verdict is that no candidate clears all four bars**, at 55/45.

---

## 12. Not done

* **Nothing is adopted and no engine constant changes.** `BETA_SHRINK` stays `None`, and a test
  pins that this item changed no file under `valuation/engine/`.
* **The beta LADDER is not tested** — `_resolve_beta`'s corroboration rungs, the `(0, 3.0]`
  plausibility band and the `BETA_FALLBACK` constant are untouched. All three candidates are
  compared as **raw numbers**, because the band is a separate guard and applying it would mix two
  questions.
* **No cost of equity, WACC or fair value is re-derived inside the contest.** The fair-value
  consequence of §9 is reported separately, on a declared sample, and is a **consequence** rather
  than a bar.
* **No third candidate** (no Vasicek shrinkage, no fundamental beta, no sum-beta), no window other
  than 60/24, and no market other than SPY. Each is a new hypothesis.
