# HANDOFF — `BETA-FORECAST` — which beta best forecasts a name's realised beta

**2026-10-13, r1 lane.** Don's queued research (`DECISIONS.md` 2026-10-13, "RESEARCH QUEUED").
**TWO EQUITY TRIALS**, equity `N` **301 → 303**, hurdle **3.3804534623358946**. **ADOPTS NOTHING;
`BETA_SHRINK` stays `None` and a test pins that no file under `valuation/engine/` changed.**

Register `PREREG_beta_forecast.md` committed **ALONE at `67831e7`** (markdown only, zero `.py`, 242
lines, a strict ancestor asserted against git by test); trials booked at **`1c2200f` before any
contest runner existed**.

---

## 1. VERDICT — both candidates NULL, for opposite reasons

Primary population: the incumbent's **`cap ≥ $10B` tier** — 31,682 cells, 1,078 names, 63
quarterly formation months, halves split at 2015-09.

| candidate | MAE raw → candidate | paired diff | *t* (month / ticker) | its own MDE80 | bars | verdict |
|---|---|---|---|---|---|---|
| **(b) Blume** `0.67·raw + 0.33` | **0.4308 → 0.3991** | **−0.03173** | **−9.60 / −14.56** | 0.0094 | B1 ✓ B2 ✓ B3 ✓ **B4 ✗** | **NULL** |
| **(c) point-in-time sector median** | 0.4308 → **0.4486** | **+0.01784** | +3.04 / +2.81 | 0.0180 | **B1 ✗** | **NULL** |

**BLUME IS RELIABLY THE BETTER FORECASTER AND THE GAIN IS TOO SMALL TO MATTER.** It cuts mean
absolute error by **7.4%**, in **both halves** (early −0.0384 at *t* −7.37/−8.81; late −0.0276 at
−6.65/−12.57), and the effect is **3.4× its own realised 80%-power MDE**. It fails on **one bar
only**: the 0.05-beta materiality floor, which was derived from the fair value before the run.

**THE SECTOR MEDIAN IS RELIABLY WORSE** — it loses by 0.0178 beta units at *t* +3.04/+2.81, so
this is a measured loss and not a failure to detect. Its damage is **late-period only** (early
+0.00007, late +0.0283), which is worth recording: the dispersion of betas within a sector widened.

**RMSE AGREES WITH MAE ON BOTH ORDERINGS** (Blume 0.5940 → 0.5446; sector 0.5915 → 0.5977), so the
primary and the declared secondary do not disagree — unlike `DC-1`, where two definitions of one
quantity pointed opposite ways.

---

## 2. THE TWO BLUME RESULTS NOW RECONCILE INSTEAD OF LOOKING CONTRADICTORY

This is the finding that outlives the verdict.

* `wacc.py`'s `BETA_SHRINK = None` carries the note that Blume *"breached the do-no-harm bound at
  **2.491%** against a 2% ceiling"* — that is how much it **MOVES** fair values.
* This register measures how much it **IMPROVES** the beta: **0.03173 beta units**, which at item
  53's own sensitivity (**0.478% of fair value per 0.01 of beta**) is **≈ 1.52% of fair value**.
* **Re-measured here on the Index's own book, the MOVE is 5.198% (median absolute).**

**SO THE ADJUSTMENT DISTURBS FAIR VALUES BY ROUGHLY 3.4× THE IMPROVEMENT IT BUYS.** Both tests
were right, neither needed overturning, and the thing that was missing was the second measurement
beside the first. **The prior rejection is not merely upheld — it is upheld by a wider margin on
the population that matters.**

---

## 3. THE FAIR-VALUE CONSEQUENCE, on the sample declared before it ran

Every constituent of the published Valquo Index plus item 53's three worked names; **87 of 89
valued on both sides** (2 lost to a delisted/no-price name, named in the artifact).

| statistic | value |
|---|---|
| **median absolute move** | **5.198%** |
| mean absolute move | 10.064% |
| 95th percentile | 34.277% |
| **maximum** | **184.718%** |
| direction | 43 up / 42 down — **symmetric, not a systematic re-rating** |
| names moving **> 25%** | **7 of 87** |

**THE INSTRUMENT CHECK IS EXACT AND IT IS WHAT LICENSES EVERY FIGURE ABOVE: this pass reproduces
item 53's published NVDA valuation to the cent — vendor beta 2.216 → fair value $145.67**, against
item 53's *"$145.67 at its vendor beta of 2.22"*. The two were computed by different lanes on
different days.

| name | vendor β → Blume β | fair value | move |
|---|---|---|---|
| NVDA | 2.216 → 1.815 | $145.67 → $163.83 | **+12.47%** |
| KO | 0.318 → 0.543 | $57.34 → $46.92 | **−18.18%** |
| TSLA | 1.916 → 1.614 | $23.25 → $24.32 | +4.60% |

**KO IS THE CASE ITEM 53 PREDICTED AND IT IS NOW QUANTIFIED.** Item 53 observed that *"KO's low
beta of 0.32 flatters it the other way"*; shrinking that beta **up** toward 1.0 cuts its fair value
by **18.18%**. So Blume does not uniformly raise or lower values — it moves high-beta names up and
low-beta names down, which is why the direction split is 43/42 and why a one-sided summary of this
change would be wrong.

**This is a CONSEQUENCE and not a bar** (register §12): no verdict rests on it, and it is here
because the prior rejection is recorded in exactly these units, so it is the only way to put the
two results on one scale.

---

## 4. A BETA CONTEST ON THE FULL CORRECTED UNIVERSE MEASURES NOTHING, AND THAT IS MEASURED

| population | cells | names | months | sd of realised β | corr(trailing, realised) |
|---|---|---|---|---|---|
| full corrected universe | 307,286 | 7,222 | 88 | **6.348** | **0.0221** |
| **`cap ≥ $10B` (primary)** | 31,682 | 1,078 | 63 | **0.592** | **0.4201** |
| `cap ≥ $2B` (sensitivity) | 79,773 | 2,785 | 63 | 0.695 | 0.3645 |

A realised 24-month beta with an sd of **6.35** that correlates **0.02** with its own trailing
value is noise: microcap monthly returns are mostly illiquidity, and this universe carries **63.3%
of weight under $300M**.

**AND THE SHARPEST CONSEQUENCE: THE ONLY POPULATION WHERE BLUME'S GAIN WOULD CLEAR THE MATERIALITY
FLOOR IS THE ONE WHERE THE TARGET CANNOT BE MEASURED.** The gain rises monotonically as the
universe widens — **0.0317** at `$10B`, **0.0464** at `$2B`, **0.0847** on the full universe — and
0.0847 **would** clear 0.05. That reading is foreclosed by the register, written before the loss
was computed, and this is the measurement that shows why the foreclosure was necessary rather than
fussy: a candidate looks most useful exactly where the thing it is forecasting is unmeasurable.

**SECTOR COVERAGE INDEPENDENTLY REPRODUCES `S25`.** The dated GICS map covers **94.8%** of the
tier's cells (30,033 of 31,682) — **the same 94.8% `S25` published** — against **37.94%** of the
full universe. That is the confirmation that S25's figure was always a megacap-tier number, and it
was not something either lane set out to check.

---

## 5. WHAT WAS NOT RE-OPENED, AND WHY THIS IS A SECOND MEASUREMENT RATHER THAN A RETRIAL

**The prior rejection stands.** It answered *how much do fair values move* — a do-no-harm bound on
128 live names, resolving **0 of 6** decisive names, and `HANDOFF_live_data_bugs.md` records the
anti-tuning rule that rejected it rather than retuning it. **This register asked whether the raw
beta is the best available FORECAST, which had never been tested here.** A candidate can fail a
do-no-harm bound and still be the better estimator; that is now measured in both directions and
the record holds both.

---

## 6. METHOD NOTES THAT A SUCCESSOR NEEDS

* **There is no historical vendor beta**, so candidate (a) is the vendor's own construction
  recomputed from the price cache — a **declared substitution**, licensed by `valuation/data/beta.py`
  reproducing the vendor's column to a worst absolute difference of **0.036** (JPM), not assumed.
* **The two beta windows cannot overlap** — produced by one function, with a test asserting their
  intersection is empty and that the trailing window **ends at** the formation month while the
  forward window **starts strictly after** it. That off-by-one is the only way this design could
  leak.
* **Candidate (c) uses `S25`'s DATED map and never the panel's `sector` column**, which is
  **TODAY's** classification; using it in a forecasting contest would hand the candidate under
  test knowledge of the future. Pinned over the AST.
* **The vectorised estimator is gated against the explicit per-cell loop at max |Δ| 1.5e-14 over
  1,709 cells, with the comparison COUNT asserted** (`MB21`'s `C1` scored a perfect zero by
  comparing nothing). The loop would have taken hours on 9,645 names; a faster path returning a
  different number is worthless.
* **The cluster-robust mean is DELEGATED to `dipcall_arm.clustered`** — the same estimator
  `INSIDER-CLUSTER` used an hour earlier. One cluster-robust mean in this repository (`B7`).
* **The MDE travels with the verdict and is this contest's own** (`MB8`), on the worse clustering
  because B2 requires clearing under both. **It came in at 0.0094 against the register's worst-case
  bound of 0.0548** — the design was ~6× better powered than the pre-outcome bound suggested,
  because the `sqrt(n/G)` inflation assumes perfect within-cluster correlation. **The register said
  the floor sat at a knife edge against that bound and it did not**, which is the direction worth
  recording: the conservative bound was conservative.

---

## 7. BUGS FOUND

* **MINE: `blume()` takes a scalar and was handed a Series**, which raised rather than
  broadcasting. Fixed by mapping through the same function instead of widening its signature —
  **a function that silently accepted either is what lets a Series-shaped bug through somewhere
  else.**
* **MINE: a hand-typed HLZ hurdle literal was wrong in the fourth decimal** (3.3807018494367414
  against the derived 3.3804534623358946). Caught by deriving it from `statistics.hlz_hurdle`
  before committing — which is exactly what `tests/test_research_log_integrity.py`'s own note says
  to do, and the reason it says so.
* **REPORTED, OUTSIDE THIS LANE:** `S25`'s published **94.8%** sector coverage is a **megacap-tier**
  figure, not a universe figure — it is **37.94%** on the corrected full universe. Nothing in
  `S25`'s own record is wrong (it measured the S23 valuation panel and said so), but a successor
  reading "94.8%" as a property of the corrected universe would be out by 2.5×.

---

## 8. IF DON WANTS TO ADOPT ANYWAY — the two consequences, as the register requires

Blume **is** the better estimator and the verdict is NULL only on materiality, so this is a real
decision rather than a closed door. Two things must be stated with it:

1. **IT CHANGES EVERY PUBLISHED FAIR VALUE** — median **5.198%** on the Index's own book, 7 of 87
   names by more than 25%, one by 185%. Beta enters the cost of equity for every DCF the product
   shows, so this is a construction change with the blast radius of the whole valuation page and
   therefore **a vintage event**. Under `DECISIONS.md` 2026-10-06 any candidate is quoted at **half
   its backtested size** (McLean-Pontiff).
2. **`VALREADS` RECORDS THE VALUATION PAGE'S READS AS COMPUTED, SO A MID-RECORD CHANGE NEEDS A
   DATED AMENDMENT TO `PREREG_valuation_reads.md` BEFORE IT SHIPS.** That register began a weekly
   append-only record of `price_vs_model`, `price_implied_growth` and the rest **on the explicit
   basis that the reads are recorded as served**. Changing beta changes `base_value` and therefore
   `price_vs_model_pct` for **every** name, so the record would hold two incomparable regimes with
   nothing marking the seam — and that register's §8.1 makes an unannounced construction change a
   **void condition**. The amendment must be **dated, committed alone, and must name the first
   recorded week scored under the new beta.**

---

## 9. NOT DONE

* **Nothing adopted; `BETA_SHRINK` is still `None`**, pinned by test.
* **The beta LADDER is untested** — `_resolve_beta`'s corroboration rungs, the `(0, 3.0]`
  plausibility band and `BETA_FALLBACK` are untouched, and all three candidates were compared as
  **raw numbers** because the band is a separate guard and applying it would mix two questions.
* **No third candidate** — no Vasicek shrinkage, no fundamental beta, no sum-beta — **no window
  other than 60/24**, and **no market other than SPY**. Each is a new hypothesis.
* **The `$2B` sensitivity and the full-universe reading carry NO verdict** and were declared in the
  register so neither could be promoted after the fact.
* **No optimisation of the Blume weight.** 0.67 is Blume's published value and `wacc.py`'s own
  constant; fitting it on this data would be the in-sample selection this project has paid for
  repeatedly, and `HANDOFF_live_data_bugs.md`'s anti-tuning rule already refused it once.
