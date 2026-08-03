# HANDOFF — lazy prices: does the language-change signal predict returns? (roadmap #28, the gate)

**VERDICT: REJECT. Do not wire it into the panel.**

The dataset is real, the pipeline is clean, and the signal does nothing. On 194 large-cap
survivors over 2016-2026 the whole-document similarity score has a rank-IC of **-0.0156**
(t Newey-West **-1.07**), a long-short spread of **-5.0%/yr** (t(NW) -1.19) and deciles that
run mildly BACKWARDS. It fails every bar in the pre-registered rule, and the point estimate
has the wrong sign as well as no significance.

That is a useful outcome, not a wasted one: Cohen-Malloy-Nguyen is a well-cited paper, the
idea was worth 90 minutes of EDGAR bandwidth, and it is now tested rather than assumed.

    python -m valuation.research.lazy_prices_ic                    # full run (~10 min)
    python -m valuation.research.lazy_prices_ic --no-orthogonality  # ~2 min, skips the panel
    python tests/test_lazy_prices_ic.py                             # 24 tests

Full numbers: `data/filings/lazy_prices_ic.json` (gitignored — this file is the record).

## 1. Coverage FIRST (the project rule)

| | |
|---|---|
| scored filing pairs in | 7,095 |
| dropped: stub filings under 2,000 words | 5 (all BNS — that ticker leaves the study entirely) |
| dropped: non-primary documents | 0 |
| **pairs used** | **7,090 over 194 tickers** |
| no Sharadar price history | 1 (`AMAT`) → 193 names priced |
| panel rows (month-end x ticker) | 20,055 |
| rebalance dates | 116 (111 with a scorable cross-section) |
| names per date | median 182, max 193, min 1 (the first months) |
| signal age at use | median 48 days, p95 92 days |
| form mix of the live signal | 77.5% 10-Q, 22.5% 10-K |
| window | 2016-08-31 → 2026-03-31 (last date with a full 63-day forward) |

**This is NOT the full universe, and the METHODOLOGY RULE's verdict standard is therefore
unavailable here.** 194 survivor large caps is 7% of the 2,710-name Sharadar panel, has no
delisted names in it, and covers 10 years rather than 18. That biases the study TOWARD a
positive result (survivors, the friendlier large-cap tier). It came back negative anyway,
which is what makes the rejection safe to act on — a positive would have needed re-testing
on a survivorship-free universe before anyone believed it.

## 2. The primary result

`cosine_tf` (the paper's own measure: cosine on raw term counts, corpus-free), 3-month hold,
month-end rebalance, 111 dates, ~180 names per date.

| metric | value | bar |
|---|---:|---|
| mean rank-IC | **-0.0156** | > 0 |
| IC t-stat (plain) | -1.54 | |
| **IC t-stat (Newey-West, lag 2)** | **-1.07** | > 2 |
| dates with positive IC | 38.7% | > 50% |
| long-short (D1-D10), annualized | **-5.0%** | > 0 |
| long-short t(NW) | -1.19 | > 2 |
| long-short hit rate | 47% | |
| **monotonicity** | **+0.709** | -1.0 is ideal; **+ is backwards** |
| top-decile alpha vs equal weight | **-2.9%/yr** | > 0 |
| bottom-decile alpha | +2.2%/yr | |
| equal-weight universe | +21.1%/yr | |

Decile returns, highest similarity ("laziest") first:
`18.2 / 21.2 / 19.8 / 19.0 / 17.5 / 19.4 / 22.8 / 24.1 / 26.0 / 23.3` %/yr.
The paper predicts that line should fall. It rises.

**Sign convention, stated because this project has read it backwards before:** buckets run
best-predicted-first, so monotonicity **-1.0 is perfect ordering** and **+1.0 is exactly
backwards**. +0.709 means the ranking is mostly inverted. Pinned by
`test_monotonicity_is_minus_one_when_the_signal_is_perfectly_ordered`.

## 3. Held-out, both halves

Dates split by time with a 3-period embargo on the boundary. The direction was
**pre-registered before any return was joined** — it is stated in `lazy_prices.py`'s module
docstring and in the dataset commit message from the previous session — so unlike the
`low_risk` case there is no in-sample decision here needing confirmation. What the split
tests is stability.

| half | window | mean IC | IC t(NW) | long-short | LS t(NW) | monotonicity |
|---|---|---:|---:|---:|---:|---:|
| early | 2016-08 → 2021-02 | -0.0173 | -1.24 | -4.3%/yr | -1.31 | +0.08 |
| late | 2021-06 → 2026-03 | -0.0185 | -0.76 | -6.2%/yr | -0.83 | +0.76 |

Both halves are negative and neither is significant. The sign is stable in the direction
OPPOSITE to the pre-registered one, which is the cleanest possible rejection: not "it worked
once and stopped", just "it doesn't work, consistently".

## 4. Everything else that was measured (7 measures x 4 horizons = 28 cells)

Nothing clears the bar in the pre-registered direction. Best cells by IC t(NW):
`jaccard@252` **+2.00**, `jaccard@126` +1.34, `cosine_tfidf@126` +1.29. At 28 cells, **~1.4
are expected to clear |t|>2 on noise alone**, so one marginal 2.00 is exactly the null.

Every cell clearing |t|>2 is automatically re-tested on both time halves by the code rather
than being left for a reader to quote selectively. Three did:

| cell | why flagged | early half | late half | read |
|---|---|---|---|---|
| `jaccard@252` | IC t +2.00 | IC t **+3.88**, LS t +3.23 | IC t **+0.24**, LS t -0.34 | **does not replicate** — all of it is 2016-2019 |
| `mdna_cosine_tf@21` | LS t **-2.58** | LS t -1.79 | LS t -1.96 | wrong sign, but stable — see §5 |
| `mdna_jaccard@63` | LS t **-2.49** | LS t -1.13 | LS t -2.26 | wrong sign, same effect |

## 5. The one thing that did show up — and it is backwards

The MD&A-section measure has a long-short spread of **-11.2%/yr (t(NW) -2.58)** at a 1-month
hold, present in BOTH time halves. Decomposed, it is almost entirely the BOTTOM decile:

- firms that **rewrote their MD&A the most**: **+29.9%/yr** (+8.6pp vs the +21.3% universe)
- firms that barely touched it: 18.7%/yr (-2.6pp)

It survives an MD&A word floor (t(NW) -2.60 at ≥1,000 words, -2.25 at ≥3,000), so it is not
the "no material changes" boilerplate artifact. **This is the opposite of the paper's claim.**

**It is not being adopted, and it is not being flipped.** Reasons, in order of weight:
1. The direction was pre-registered. Reading a negative result backwards is a NEW hypothesis
   that needs its own out-of-sample test — it does not inherit this one's evidence.
2. It is 1 of 28 cells, at |t| ~2.5, where ~1.4 false positives are expected.
3. The IC is ~0 (t -0.45) while the decile spread is significant: this is a tails-only
   effect, not a cross-sectional relationship. Tails on ~19 names a bucket are noisy.
4. The obvious explanation is that it is a **growth proxy in a growth-led decade** — the
   companies rewriting their MD&A most in 2016-2026 being the ones whose businesses changed
   most. **That check was run and does NOT support the simple version**: at the panel's
   dates the MD&A score correlates +0.029 with the `growth` theme and +0.022 with
   `momentum` (largest exposure of any theme is -0.077 to `size`). Which does not clear it —
   `growth` here is fundamentals-based revenue/asset growth, not "how much the business
   changed" — but the easy dismissal is not available either.

So it is an unexplained, wrong-signed, tails-only effect in a survivor sample. If anyone
pursues it, it starts from zero evidence, needs the survivorship-free universe, and needs a
direction pre-registered before the first return is joined.

## 6. Orthogonality

Measured on the live theme panel restricted to these names (49 dates, 8,970 rows, 37 with a
usable cross-section).

- **Correlation with every existing theme is negligible**: `value` +0.069, `quality` +0.062,
  `growth` +0.032, `insider` -0.036, `size` -0.028, `low_risk` +0.027, `capital_discipline`
  +0.014, `institutional` +0.004, `momentum` +0.003, `sentiment` empty.
- **Raw IC on the panel dates -0.021 (t -1.25); residual IC after regressing out all themes
  -0.001 (t -0.06).** Nothing survives, and nothing was there to start with.
- **Incremental**: adding it to an equal-weight theme composite at one theme's weight (0.125)
  moves the long-short from +6.6% to +4.6%/yr and its t(NW) from 0.78 to **0.68**. It makes
  the composite slightly worse.

So the signal IS genuinely orthogonal to everything the panel already carries — it just has
no information to contribute. Orthogonality was never the binding constraint.

The MD&A measure was attached to the same panel build (`orthogonality_by_measure` in the
JSON) to answer the §5 question: correlations `size` -0.077, `low_risk` +0.074, `growth`
+0.029, `momentum` +0.022, everything else under 0.06; residual IC +0.010 (t 0.65); added to
the composite it takes the long-short from +8.8% to +4.5%/yr. Independent of the themes, and
still not worth carrying.

## 7. Method notes worth keeping

- **Point-in-time in three places**: a score is usable only from `available_from`, and the
  panel requires `available_from < rebalance_date` STRICTLY (EDGAR filings often land after
  the close, so same-day use is a free look-ahead); forward returns run forward only; and the
  similarity numbers were themselves computed against a point-in-time IDF corpus. A test
  covers each.
- **Every t-stat is Newey-West corrected.** Monthly observations of a 3-month forward return
  overlap by two thirds; the plain t-stat treats them as independent and here it ran ~40%
  hotter than the corrected one (-1.54 vs -1.07). Quote the NW figure.
- **A persistent signal against persistent returns makes the per-date IC nearly constant**,
  and a near-zero-variance IC series produces an enormous t-stat no matter how spurious the
  underlying correlation is. This surfaced as a test failure while building the null case and
  it is a live hazard for any slow-moving factor, not a fixture quirk. The null test now
  checks calibration across 10 independent draws instead of trusting one seed.
- **Form mix was controlled**: 10-Ks and 10-Qs have different similarity distributions and any
  month-end cross-section mixes both, so a raw ranking partly ranks FORM. Z-scoring within
  form first changes nothing here (IC -0.010, t(NW) -0.73), which rules that out as the reason
  for the null.
- **Staleness cap 120 days** — a score is dropped rather than carried once its filing is more
  than a quarter old. Median age in use is 48 days.
- `build_panel` originally took 97s a pass, which made a 28-cell grid impractical; it is now
  1.5s via searchsorted over per-ticker filing arrays.

## 8. What this does and does not settle

**Settled:** the language-change signal, as measured on this dataset, does not predict
returns in large-cap US survivors 2016-2026, at any of four horizons, on any of seven
measures, and it adds nothing to the existing composite. Roadmap #28 is closed as REJECTED.

**Not settled:** the paper's original result was on the full CRSP cross-section including
small caps from 1995, where the effect is documented as strongest in smaller, less-covered
names — exactly the tier this survivor large-cap dataset excludes. So this is evidence that
the effect is absent HERE, not that the paper is wrong. Re-testing it properly would mean
downloading filings for a survivorship-free universe (the fetch scales linearly: ~1 doc/sec,
so another 250 names is another hour), which is a real cost for an idea that has now failed
its cheap test. **Recommendation: do not spend it.** Roadmap #15 (PEAD from EVENTS) and #16
(the ML tree combiner) are better uses of the same effort.

Nothing was wired into the live panel; `test_lazy_prices_ic.py` asserts no production module
imports either research module. `HANDOFF_STATUS.md` was deliberately not touched — parallel
agents own it. `test_edge.py` still passes.
