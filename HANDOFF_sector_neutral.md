# HANDOFF — sector-neutral (industry-relative) ranking

**Session date:** 2026-08-02
**Branch:** `worktree-sector-neutral` (auto-lands to `main`)
**Task:** roadmap #13 — populate the panel's sector column, then test industry-relative ranking
under the project's normal discipline and keep or reject it honestly.

## Verdict in one line

**REJECT. `sector_neutral` stays OFF.** It fails the pre-committed held-out gate in both split
directions, under both the flat comparison weights and the deployed weights. This is the second
independent rejection (P10 was the first), on a panel that has since gained several new signals.

## What I actually found first: the task was already done

`PROMPT_sector_neutral.md` describes this as blocked wiring work. It is not — commit `8c21ef8`
(P10, 2026-07-31) already downloaded Sharadar TICKERS, wired `metrics["sector"]`, ran the
comparison, and rejected it. I did not take that on trust, and I did not redo it blindly. I
verified the wiring is genuinely live and re-ran the experiment from scratch.

Two prompt deliverables genuinely **were** missing, and that is the real gap this session closes:

- there was **no test** pinning the wiring, and
- there was **no handoff** recording the ON-vs-OFF numbers (P10's write-up recorded only the
  held-out table — no PBO, no Deflated Sharpe, no monotonicity, no full-sample line).

The P10 comparison was run ad-hoc from a throwaway script and thrown away, so nothing on disk
would have caught the feature silently reverting to inert.

## The wiring is real (this is the part that was a bug for years)

`build_frame`'s sector-neutral path subtracts each name's **sector median** from every granular
number before the global z-score. The panel used to hard-code `"sector": ""` on every row, so it
grouped on a **constant** — `x - median(x)` over one group is a pure shift, and the z-score that
follows is shift-invariant, so turning the toggle on produced **byte-identical** output. Inert,
silent, for the project's entire history.

Confirmed live on the full universe:

| | |
|---|---|
| panel rows with a non-blank sector | **136,478 / 136,478 (100.0%)** |
| panel names with a sector | **2,710 / 2,710** |
| distinct sectors | **11** |

And the toggle now moves the numbers — mean absolute change in each theme, ON vs OFF, over the
136,478 shared rows:

```
low_risk 0.297   momentum 0.205   size 0.174   value 0.148
institutional 0.140   growth 0.121   quality 0.092   capital_discipline 0.052
insider 0.000 (a rescaled percentile, not a z-scored input — correctly unaffected)
sentiment n/a (empty theme)
```

## The experiment

Full ~2,710-name universe, **not** a subset (methodology rule). 2,827 tickers in, 2,710 usable,
136,478 panel rows, 110 rebalance dates, ~18 years. Both panels built from **identical** inputs
in the same process — the only difference is the `sector_neutral` flag. Held-out gate is
`holdout_compare_panels()`: split by time, embargo the boundary date (2012-10-08), and require
the **already-committed** margins (`MIN_HOLDOUT_TSTAT_GAIN` +0.25, `MIN_HOLDOUT_ALPHA_GAIN`
+100bps) in **both** directions.

### Under the DEPLOYED weights (`WEIGHTS_ESTABLISHED`, low_risk/sentiment zeroed)

This is the one that matters — it is what actually trades.

| | OFF | ON | |
|---|---|---|---|
| long-short t | 3.396 | **3.896** | better |
| long-short ann | +17.16% | +15.25% | worse |
| long-short hit | 64.5% | 66.4% | better |
| top-decile alpha | **+11.82%** | +10.24% | **worse (−1.58pp)** |
| signal-weighted top-decile alpha | +12.78% | +11.41% | worse |
| monotonicity | **−0.952** | −0.915 | worse (−1.0 is ideal) |
| PBO | **26.7%** | 46.7% | **much worse** |
| Deflated Sharpe | 0.999995 | 0.999928 | ~equal (both saturated) |

Held-out gate:

| split | long-short t | top-decile alpha | |
|---|---|---|---|
| early half (55 dates) | 2.578 → **3.526** (+0.948) | +14.62% → +12.65% (**−1.97pp**) | fail |
| late half (54 dates) | 2.318 → **1.812** (−0.505) | +9.21% → +7.95% (**−1.26pp**) | fail |

**VERDICT: reject.**

### Under the flat 0.125 comparison weights (`holdout_compare_panels` default)

| | OFF | ON |
|---|---|---|
| long-short t | 1.038 | 1.013 |
| top-decile alpha | +6.62% | +6.13% |
| monotonicity | −0.697 | −0.564 |
| PBO | 20.0% | 40.0% |
| Deflated Sharpe | 0.903 | 0.952 |

| split | long-short t | top-decile alpha | |
|---|---|---|---|
| early half | 0.672 → 0.791 (+0.120) | +7.75% → +8.00% (+0.25pp) | fail |
| late half | 0.968 → 0.669 (−0.300) | +5.73% → +4.46% (−1.28pp) | fail |

**VERDICT: reject.** Same answer, so the verdict does not rest on a choice of weighting.

## Why it fails — the interesting part, not just "it didn't work"

Sector-neutral is **not** noise here. It does something real and consistent: it **buys
long-short t-stat and sells top-decile alpha.** Under deployed weights the market-neutral spread
gets tighter and more reliable (t 3.396 → 3.896, hit rate 64.5% → 66.4%) while the annualised
spread and the long book both shrink.

That is a coherent story. Removing accidental sector bets removes a source of *variance* from the
long-short spread, which flatters the t-stat — but a chunk of the top decile's *return* was
coming from genuine cross-sector selection (cheap sectors really were cheap), and neutralising it
throws that away. **Valquo trades a long-only book**, so top-decile alpha is the metric that pays
and the t-stat improvement is not a trade we want.

Three further reasons not to be tempted:

1. **It is worse on both metrics in the LATER half** — the more relevant period.
2. **PBO nearly doubles** (26.7% → 46.7%), approaching the 50% coin-flip line.
3. **Monotonicity degrades** (−0.952 → −0.915): the decile ordering gets *less* clean, which is
   the opposite of what a genuinely sharper ranking should do.

The one direction that looked good — early-half t +0.948, comfortably past the +0.25 margin — is
exactly the kind of single-split result the two-direction gate exists to kill. It reverses sign
in the other half.

## Look-ahead caveat, stated not hidden

Sharadar TICKERS carries **today's** classification, so applying it to a 1998 row assumes the
company was in the same sector then. Reclassification is rare and is not return-predictive, so
this is normally considered benign — but it is **the one non-point-in-time input in an otherwise
strictly point-in-time panel**, and that is a reason to be *more* sceptical of a positive sector
result, not less. It rejected anyway, so nothing rests on it.

## What shipped

- **`tests/test_sector_neutral.py` — 6 tests, all passing.** New file (no edits to
  `tests/test_edge.py`). Pins the wiring, deliberately **not** the verdict:
  - with real sectors the toggle must change the composite (this is the test that would have
    caught the original bug — pre-P10 it would have failed);
  - with blank sectors it must be a **provable exact no-op** (the shipped bug's signature);
  - the **sector** median is subtracted, not the global median (a plausible wrong implementation
    would still "change the numbers" and pass the first test);
  - `build_fundamental_panel` no longer hard-codes an empty sector;
  - `ticker_meta` is case-insensitive and degrades to `{}` when the TICKERS cache is absent.
- **`CLAUDE.md`** — the two stale bullets calling this BLOCKED / INERT corrected in place. The
  project's memory said "there is no sector/industry column anywhere on disk", which has been
  false since 2026-07-31.
- **No source changes.** The panel wiring was already correct; nothing in
  `valuation/edge/fundamental_panel.py` needed to change, so I changed nothing.

## Suites green

| suite | |
|---|---|
| `tests/test_sector_neutral.py` | **6/6** (new) |
| `tests/test_edge.py` | **123/123** |
| `tests/test_bulk.py` | **14/14** |
| `tests/test_screener.py` | **32/32** |

## Recommended next step

**Do not re-open full sector-neutral ranking.** Two independent full-universe rejections, and the
mechanism is now understood rather than mysterious.

The one variant still worth a cheap test: **sector-relative applied to the VALUE theme alone.**
Value is where cross-sector distortion is most defensible on theory (a 6% earnings yield means
something different in utilities than in software), and it is the theme where whole-sector
mispricing is most likely to be a real bet rather than an accidental one. Everything needed is
now on disk and pinned by tests, so it is a one-parameter experiment rather than a data project.

Also worth noting for whoever picks this up: the sector column is **already used** for a
different and *accepted* purpose — the `max_sector_w` concentration cap on the book. That is a
risk control, not a re-ranking, and this rejection says nothing about it.
