# PRE-REGISTRATION — V3, noise-calibrated hot score (lane r1)

Committed **before any calibration number exists**. Written against `VALQUO_EXTENSIONS.md` item V3
(adopted by Don 2026-08-09). Nothing in this file is restated from a result; if a number appears
below it is a property of the INPUT (row counts, seeds, ladder positions), measured before the
question was asked.

---

## 1. The question

X7 calibrated the *research* bars by asking what the pipeline reports when the signal is
definitionally nothing. The *product* has never been asked the same question. The live hot score
is a percentile rank of a composite, and a high composite asserts something specific to a reader:
**this name is strong across several themes at once.** That assertion has never been measured
against what chance produces.

So: **if the individual theme numbers were exactly as they are, but their co-occurrence within a
single name were pure chance, how good would the top of the book still look?**

## 2. What is scored, and by what code

The **live** composite path, imported read-only. No file under `valuation/` is edited by this item.

```
valuation.screener.attribution.decompose(df, S.WEIGHTS_ESTABLISHED, S.WEIGHTS_SPECULATIVE, soft=True)
hot_score = composite.rank(pct=True) * 99 + 1        # screen.py:246
rank      = composite sorted descending               # screen.py:247-248
```

Live weights as deployed (`settings.py`), seven active themes per bucket — `low_risk` and
`sentiment` carry weight 0.0 and therefore do not participate:

* established: `value, quality, momentum, insider, capital_discipline, size, institutional`
* speculative: `value, growth, momentum, insider, capital_discipline, size, institutional`

**LIMITATION COMMITTED IN ADVANCE, not discovered afterwards.** The panel carries no `value_est`,
`value_spec` or `op_margin` column, so `decompose` takes its documented **hard-bucket branch**
(`attribution.py:90-101`) rather than the soft blend. What IS the live path here: the deployed
weights, within-bucket standardization, and renormalization by the present-weight mass — i.e. the
structure of the score. What is NOT exercised: the soft blend of the two `value` branches by
`p_established`. The output must state this itself. It affects how one theme is built, not how the
composite is formed, so it is a caveat on transfer to the live book, not on the internal comparison
— real and null are scored by the identical call.

## 3. Data

`data/free_analysis/panel_corrected_69d.pkl` — the corrected 69-date panel every session since
2026-08-06 has used. 113,945 rows, 69 dates, `bucket` present (90,533 established / 23,412
speculative).

* **Primary cross-section: the latest date, 2026-01-28, n = 1,842 names.** This is the closest
  available stand-in for "the book the product would show".
* **Robustness set: all 69 dates.**

**Why not a live scan.** A several-hundred-name live fetch throttles the Yahoo quota and silently
returns empty company data, which would make every bound pass vacuously. The panel's theme columns
are built by the same `build_frame` the live path uses, so this is the same object without the
network failure mode.

## 4. The permutation schemes

Both operate **within (date, bucket) groups**, on the ten theme columns only.
`ticker`, `bucket`, `sector`, `market_cap` and `fwd_ret` are untouched — the X7 convention.

**H1 — PRIMARY NULL: coverage-preserving, within-column permutation.**
For each group and **each theme column independently**, permute the OBSERVED values among the rows
that have them; leave every NaN exactly where it is.

Preserved exactly: each theme's marginal distribution within each bucket; each theme's coverage;
and **each row's coverage pattern**, hence its renormalization denominator (`_branch`'s `denom`).
Destroyed: **cross-theme agreement within a name** — precisely the thing a high composite asserts,
and nothing else. Because the per-row denominator is identical between real and null, any
difference in the composite distribution is attributable to agreement alone and not to coverage.

**H0 — CONTROL: X7 block permutation.** The whole row's theme vector shuffled together within
(date, bucket), i.e. X7's own scheme.

> **PREDICTION COMMITTED NOW: H0 is a near no-op on the composite distribution.** A row's theme
> vector and its denominator both travel intact and only the ticker label changes, so the composite
> quantiles should match the real ones to within Monte Carlo error. This control is run *because*
> X7's scheme was designed for return-based statistics and is expected to be uninformative about a
> score — running it makes that explicit and measured instead of asserted.
>
> **If H0 moves the composite distribution materially, the run is a HARNESS FAILURE and no
> calibration is quoted from it.**

## 5. Draws and seeds

X7 convention, `seed0 + k`:

| arm | dates | draws | seeds |
|---|---|---|---|
| H1 primary | 2026-01-28 | 500 | 3000..3499 |
| H0 control | 2026-01-28 | 500 | 3000..3499 |
| H1 robustness | all 69 | 100 each | 3000..3099 |

## 6. The statistic

Per draw, on the scored cross-section sorted by composite descending:

* **composite at each rank of the ladder** k ∈ {1, 2, 3, 5, 10, 15, 20, 25, 50, 100, 184}
  (184 = the top-decile boundary of the 1,842-name primary cross-section);
* the **mean composite of the top decile**;
* the top decile's **mean count of themes present** (the coverage of the book);
* the top decile's **mean absolute contribution share per theme** — the *composition*.

**The deliverable calibration table**: for each ladder rank k, the H1 noise p50 / p90 / p95 / p99 /
max, and the empirical p = the fraction of noise draws whose composite-at-rank-k is ≥ the real
value. Read as: *"a #k-ranked name with composite ≥ x occurs in fewer than y% of noise universes."*
Plus one plain sentence per rank band, written for the product.

## 7. Pre-committed verdict rule

**Primary statistic: the composite at rank 10 on the primary cross-section.**

* **DISTINGUISHABLE** — real ≥ the H1 noise **p95** (empirical p ≤ 0.05).
* **NOT DISTINGUISHABLE** — real < the H1 noise p95. **Consequence accepted in advance: the
  product's confidence language for that rank band must weaken.** V3 says an unflattering answer
  ships too, and this is the sentence that makes that binding rather than optional.
* **NULL / no verdict** — anything else, including the control failing.

**Generality gate.** The verdict is quotable as a property of *the product* only if it holds on
**≥ 42 of the 69 dates (60%)**. Below that it is quoted as a property of the primary cross-section
only, and said so in the same sentence.

Ambiguous against this rule is a **NULL**, not a judgement call (RUN_RULES A6).

## 8. Directional expectation, recorded because this project's expectations keep being wrong

**I expect DISTINGUISHABLE at rank 10, 70/30.** Reasoning: the deployed themes are net positively
correlated, so the real composite should have a wider cross-sectional spread than an
agreement-destroyed null, and the extreme order statistics should separate further still.

**The stated risk to that expectation:** the theme correlation matrix is not uniformly positive —
the record has `low_risk`/`size` at −0.352 — and `low_risk` carries weight 0.0 in the live weights,
so the seven that actually participate may be less correlated than the nine-theme intuition
assumes. If the active seven are close to independent, the real book will look no more extreme than
noise; if their net correlation is negative, it could look **less** extreme. Both are live
possibilities and both ship.

## 9. Trial cost

**ZERO.** This searches no hypothesis space, fits nothing, and adopts nothing — it is a
calibration, on the session-10 precedent ("a calibration searches nothing, equity `N` stays 121").
**Equity `N` stays 130** (measured today from `research_log.detail()`; note CLAUDE.md still says
129, which is one session stale). No weight, threshold, or shipped behaviour changes as a result of
this run. If any of that stops being true, the arms become trials and are logged as such.

## 10. Storage

RUN_RULES A9 — **every draw is stored, not just the percentiles.** Per-draw rank ladders go to CSV
alongside the JSON summary, and the inputs to every derived statistic are banked so a later
re-denomination is arithmetic rather than a re-run.

---

Report: `HANDOFF_extensions_v3.md`. Script: `scripts/score_calibration.py` (new file).
Artifacts: `data/free_analysis/SCORE_CALIBRATION.json` + `.draws.csv`.
