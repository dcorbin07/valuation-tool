# Finding the best parameters without fooling yourself

_The protocol Valquo uses to tune itself, why each piece is there, and how to run it._

Run it: **`param_search.bat`** (or
`python -m valuation.edge.fundamental_panel --data-dir data/backtest --param-search --permutations 25`).
Code: `valuation/edge/param_search.py`. Tests: `python tests/test_edge.py`.

---

## 0. The thing to internalise first

There is no search method that finds better parameters. Every optimiser — grid, Bayesian,
CMA-ES, genetic — finds a **higher in-sample peak**, and the better it is at climbing, the more
of that peak is noise. The out-of-sample surface is nearly flat and it drifts. So a sharper
peak-finder usually *lowers* your real-world result.

What actually determines the answer is **how you decide a parameter is better**. That decision
procedure is the only thing worth engineering, and it is what this module is.

This is not a slogan, it is measured. Run this exact search over hundreds of configurations on
**data containing no signal whatsoever** and the winning configuration comes out looking
**+3% to +4.7%/yr better than the baseline**, gross of costs, run after run. That is the noise
floor of the search itself. Any procedure that cannot subtract that number is not measuring an
edge, it is reporting it.

Two further things fall out of the same measurement, and neither is obvious in advance:

- On signal-free data every configuration loses about **1%/yr** to turnover, and a config that
  merely trades less beats the baseline with a **t-stat of +3.8** — no skill involved. So the
  significance tests run on *gross* returns and costs get their own gate (§5, §7).
- The Hansen SPA test — the textbook instrument for exactly this problem — has a **35%
  false-positive rate** in this application, not 5%. It is not broken; its null is just the wrong
  one here. Hence the permutation null, not SPA, is the gate (§5a).

---

## 1. The seven stages

### Stage 0 — Lock a hold-out before looking
The most recent 20% of rebalance dates are carved off before anything is fitted, searched, or
plotted, and are touched exactly once, at the very end. Nothing else in this codebase has a
genuinely untouched set — CPCV re-uses every date many times by design.

This is the weakest of the tests statistically (one path, few periods) and the hardest to cheat.
Keep it that way: if you ever tune anything after seeing it, it is dead and you need new data.

### Stage 1 — Declare the whole search space in one place
Previously weights were selected under CPCV and trade parameters under the weaker single-path
walk-forward. Two separate searches means the true number of trials is unknown, and every
multiple-testing correction needs that number. So everything tunable is one joint space:

| axis | values | notes |
|---|---|---|
| `scheme` | the 8 weighting schemes | categorical |
| `top_n` | 10, 15, 20, 25, 30, 40, 50 | how many names held |
| `exit_band` | 1.5, 2.0, 3.0, 4.0 | hysteresis: sell when rank > band x top_n |
| `min_hold` | 1, 2, 3, 4 | periods before a sell is allowed |
| `cap_tier` | all, top66, top33, top10 | point-in-time market-cap tilt |

= 3,584 configurations. That number is the honest trial count, and it is what gets penalised.

### Stage 2 — Score every config on the *same* CPCV paths
Combinatorial Purged CV chops the timeline into 6 blocks and holds out every pair (15 paths),
purging the periods adjacent to each test block so a 63-day forward return cannot leak across the
boundary. Every configuration sees identical paths, which makes the comparisons paired and
preserves the correlation structure the bootstrap tests need.

### Stage 3 — Optimise the objective you actually deploy, net of costs
The old selection maximised **IC** while the book earns **top-decile alpha**. Optimising a proxy
and reporting the target is a silent mismatch. Here the objective is the thing we run: per-period
alpha of the hold-until-it-drops-out portfolio versus the equal-weight universe, **minus turnover
x 25bps**. Without the cost term, selection drifts toward high-churn settings for free.

### Stage 4 — Select by robustness, not by the highest number
Three rules, and they matter more than anything else in this document:

1. **Lower confidence bound.** Rank on `mean - 1 SE` across the 15 paths, not the mean. A config
   that wins on average but swings wildly across paths loses to a steadier one.
2. **Plateau smoothing.** Score each config as the average of itself and its neighbours along the
   *ordered* axes. A lone spike gets pulled down to its surroundings; the centre of a broad hill
   survives. Smoothing never crosses `scheme`, because weighting schemes are categorical — "ic-ir"
   is not adjacent to "risk-parity" in any meaningful sense.
3. **Interiority.** A value sitting at the edge of the grid is untested on one side, so it cannot
   be called the centre of a plateau, and it is not adoptable. If the unrestricted best is on an
   edge, the report says so and tells you to widen that axis and re-run. (Ends that are *natural*
   limits — `min_hold=1` means no constraint, `cap_tier=all` means the whole universe — are not
   treated as edges, because nothing exists past them.)

The report always shows what a naive `argmax` would have picked, so the cost of being careful is
visible rather than hidden.

### Stage 5 — Test the winner against the whole search

> **These tests run on GROSS alpha, and that detail is load-bearing.** Cost differences between
> configs are systematic, not statistical. Measured on completely signal-free data, a config that
> merely trades less beats the incumbent with a t-stat of **+3.8** — no predictive power involved,
> just a smaller commission bill. Run the significance test on net performance and it dutifully
> reports a "highly significant edge" that is pure turnover. Stripping costs out makes the test
> answer the only question worth asking: *is any config genuinely better at picking the stocks?*
> The cost dimension is judged separately, by the decomposition in Stage 7 and its own gate.

- **White's Reality Check** and **Hansen's SPA test**, via a stationary block bootstrap on the
  per-period performance differentials of every config against the baseline. These ask the only
  question that matters — *given that I tried all 3,584 of these, how likely is a best-of-3,584
  this good by luck?* — and because they bootstrap the family jointly they account for our configs
  being heavily overlapping, which the `sqrt(2 ln N)` haircut cannot.

  **These are reported as diagnostics and are deliberately NOT gates.** See §5a — that decision
  is measured, not stylistic.
- **PBO** (probability of backtest overfitting) — how often the in-sample winner lands below the
  out-of-sample median.
- **Deflated Sharpe**, fed from a **persistent trials ledger** (`data/backtest/trials_ledger.json`).
  Every distinct config ever evaluated is remembered across runs. Without this, re-running a
  search with a slightly tweaked space quietly launders away the multiple-testing penalty, and the
  DSR you quote is meaningless.

### Stage 5a — Why the textbook test is not the gate (calibrate your tests)

Do not trust a significance test because it is published. Test the test.

Running this entire protocol on **20 independent signal-free panels** — data where the correct
answer is known to be "there is no edge" — the Hansen SPA test returned **p < 0.05 on 35% of
them**. As a 5%-level gate it is wrong by a factor of seven.

It is not a coding error, and the check that proves it is worth copying. Hand the test the *same*
differential matrix with every column demeaned, so the null is true by construction: it then
returns **p ≈ 1.0 every single time** — conservative, exactly as advertised. The implementation is
fine.

The problem is the question. SPA's null is "no config beats the benchmark", and the benchmark
enters as **one realisation**. When that single realisation is unlucky — and with 3,584 correlated
configs it often is — essentially the entire family beats it (on one signal-free panel, 99% of
configs beat the baseline by an average of +2.7%/yr), and SPA correctly rejects a null that was
false for reasons that have nothing whatsoever to do with predictive skill.

The permutation null has no such weakness, because it resamples the baseline's own luck along
with everything else. So: **permutation is the gate, SPA and RC are diagnostics**, and the report
prints that warning next to them so a small p is never misread as evidence.

### Stage 6 — The permutation null (the one that assumes nothing)
Shuffle forward returns within each date — destroying all predictive signal while keeping the
cross-sectional structure, the fitting procedure and the search space identical — and **re-run the
entire selection**. Do that 25+ times. The spread of "best config found" is the empirical noise
floor of your own procedure, and `p` is the fraction of signal-free re-runs that beat the baseline
by at least as much as the real one did.

This is the check that catches leakage that theory cannot see, and it is the one to trust when the
parametric tests disagree with it. Note you need **at least 20 permutations** for `p < 0.05` to be
attainable at all; the code warns you if you ask for fewer.

### Stage 7 — Where did the improvement come from?
With turnover cost inside the objective, "trade less" beats the incumbent *even when the signal is
worthless* — a real economic gain, but not better stock picking. So the selected config is re-scored
gross of costs and the improvement is split:

```
net improvement = better SELECTION (gross edge) + lower turnover cost
```

An "improvement" that is entirely cost saving is a turnover finding, and it is reported as one.

---

## 2. The gate

Adoption requires **all** of:

| gate | threshold | what it rules out |
|---|---|---|
| `permutation_pvalue_lt_0.05` | empirical p < 0.05 | best-of-N luck — the procedure's own noise floor |
| `pbo_lt_0.50` | PBO < 50% | in-sample winners that don't generalise |
| `deflated_sharpe_gt_0.95` | DSR > 95% | multiple testing + non-normal returns |
| `positive_in_60pct_of_paths` | >= 60% of CPCV paths | edges that live in one regime |
| `improvement_is_not_just_lower_turnover` | gross edge > 0 | cost savings mislabelled as alpha |
| `beats_baseline_on_holdout` | on locked data | anything the above missed |

Reported but **not** gates: Hansen SPA and White RC p-values (see §5a — measured 35% false-positive
rate in this application), and the naive `argmax` config, shown so the cost of robust selection is
visible.

**Individually most of these gates are weak, and that is the point.** Measured on signal-free
panels, `positive_in_60pct_of_paths` and `improvement_is_not_just_lower_turnover` each certify pure
noise **100% of the time**, and `beats_baseline_on_holdout` about a third of the time. None of them
is a filter on its own. The conjunction is, which is why adoption requires all six rather than one
headline number — and why every one of them has a measured false-positive rate rather than an
assumed one.

Anything less and the answer is **keep the defaults**. That is the expected result for a weak
signal, and this module is built to say it loudly rather than to find something.

---

## 2a. The first real run (July 2026) — a worked example of why this exists

Full grid, 3,584 configs x 15 CPCV paths, 88 rebalances searched, 22 locked away (2021-01 to
2026-04), 25 permutations. `data/backtest/param_search.json`.

The search found something that looked genuinely good:

| | search window | locked hold-out |
|---|---|---|
| **selected** — `ic-proportional, top20, band2.0x, hold3, all` | **+8.43%/yr** (LCB +6.33%) | **−0.04%/yr** |
| baseline — `current-default, top25, band2.0x, hold2, all` | −0.83%/yr (LCB −2.00%) | **+5.12%/yr** |

It beat the baseline by +9.26%/yr, was positive in **87% of the 15 CPCV paths**, had a **PBO of
33%**, and the improvement was +9.15%/yr of better *selection* against only +0.11%/yr of saved
turnover — so it was not a cost artefact either. On the evidence most backtests stop at, this is a
clear winner and you would ship it.

Then the two tests that cost something to run:

- **Locked hold-out: it collapsed.** −0.04%/yr where the supposedly inferior baseline made
  +5.12%/yr. Every bit of that +8.43%/yr lived in the window the search could see.
- **Permutation null: p = 0.077.** Re-running the identical search on signal-free data produced an
  average "edge" of **+2.65%/yr**, and on one of the 25 draws **+8.59%/yr** — bigger than most of
  what the real data produced. The observed result is simply not far enough into the tail.
- Deflated Sharpe 8% against 3,584 cumulative trials.

**Verdict: keep the defaults.** Three gates failed.

Two further tells, both visible only because the protocol reports them:

- The winning *scheme changed with the grid*. A coarser first pass picked `ic-ir`; the full grid
  picked `ic-proportional`. A real effect does not depend on which values you happened to list.
- The whole top of the leaderboard sat at `hold4`, the edge of the tested range, which is why
  interiority refused to adopt it. Winners that pile up against a grid boundary are usually the
  optimiser walking downhill toward "trade less", not a genuine optimum.

The honest read: **this is what overfitting looks like from the inside** — 87% of paths positive,
PBO 33%, a large decomposed selection edge, and it is still worth nothing out of sample. Any
procedure without a locked hold-out and a permutation null would have shipped it.

---

## 3. What this does NOT fix

Be clear about the ceiling. The protocol makes the *decision* honest. It does not create signal:

- If the underlying IC is ~0.04 and the entire edge sits in one lagged quarterly 13F theme, no
  selection procedure can turn that into a credible strategy. See `CLAUDE.md` for the current
  honest findings.
- The search is only as good as its space. If the real answer is a parameter we never declared, it
  is not going to be found.
- Costs are modelled as a flat turnover charge, not a real market-impact model.
- The permutation null breaks the name-return link but keeps each date's cross-section intact; it
  tests for cross-sectional predictive signal, not for regime-timing skill.

The levers that actually move the number up are **new orthogonal data** and **validating the 13F
signal**, both in `OPTIMIZATION_RESEARCH.md`. This module's job is to stop us mistaking noise for
progress while we go and get them.

---

## 4. Running it

```bash
# full protocol (uses the cached panel after the first build)
python -m valuation.edge.fundamental_panel --data-dir data/backtest --param-search \
       --permutations 25 --json data/backtest/param_search.json

# quick look: smaller space, no permutation null
python -m valuation.edge.fundamental_panel --data-dir data/backtest --param-search --fast --permutations 0

# rebuild the point-in-time panel from scratch (slow)
... --param-search --refresh-panel
```

Flags: `--fast` (coarser space), `--permutations N`, `--cost-bps N` (default 25),
`--holdout-frac F` (default 0.2), `--refresh-panel`.

**Calibrate the gates whenever you change any of them:**

```bash
python scripts/calibrate_param_search.py 20        # 20 signal-free panels, structural check
python scripts/calibrate_param_search.py 20 25     # also calibrates the permutation gate (slow)
```

It re-runs the whole protocol on data with no signal in it and prints the noise floor plus the
false-positive rate of every gate. It exits non-zero if anything was adopted. A gate whose
false-positive rate you have not measured is not a gate — that is how the SPA problem in §5a was
found, and it would have gone unnoticed otherwise.

The panel is cached to `data/backtest/panel_cache_*.pkl`, keyed on everything that changes it, so
a stale cache can't silently be reused for different settings. The first build takes 20-40 minutes;
after that a full search is minutes.

**Do not delete `data/backtest/trials_ledger.json`.** It is the memory of how much searching we
have done, and the Deflated Sharpe is only honest while it survives.
