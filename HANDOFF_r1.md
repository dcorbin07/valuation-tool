# HANDOFF_r1 — Factor-adjusted alpha (audit item R1)

Session `r1`, 2026-08-04. Cold session: opened `PROMPT_r1.md` and the R1 entry in
`VALQUO_EDGE_AUDIT.md`, and deliberately did not read the conclusions of the sessions that
produced the inputs (X4, D3, X8) until my own numbers were final.

---

## 1. PRE-COMMITMENT — written before any regression was run

*Everything in this section was written and saved before a single number was computed. It is not
revised below. Timestamp: the commit that first added this file.*

> **The word "alpha" is permitted only if the FF5+MOM intercept is positive with Newey–West
> t > 2.0.** If the intercept is not distinguishable from zero, the honest framing is
> **efficient factor exposure** — a real thing, just a different thing.
>
> **An ambiguous result against that threshold is a NULL, not a judgement call.** t = 1.9 is a
> null. t = 2.05 with a different-but-defensible aggregation choice is a null. There is no
> "directionally positive" verdict available here.

### 1a. The two claims, both written in advance

**CLAIM A — if the FF5+MOM intercept is positive with NW t > 2.0:**

> "Valquo's top decile has produced returns that the standard five Fama–French factors plus
> momentum do not explain. After controlling for market, size, value, profitability, investment
> and momentum exposure, the model's selection adds an annualised intercept of X% (t = Y) over
> 1998–2026. That residual is what the model is actually for: it is not reachable by holding a
> factor blend, and its most likely source is the `institutional` (13F) theme, which has no
> Fama–French analogue, plus the interaction structure of combining seven themes rather than
> sorting on one."

**CLAIM B — if the intercept is not distinguishable from zero (NW t ≤ 2.0), or is negative:**

> "Valquo delivers diversified, well-documented exposure to the standard equity risk premia —
> value, quality, momentum, size, investment discipline — efficiently and transparently, with a
> public forward track. Its returns are explained by factor exposure rather than by security
> selection the factors miss. That is a legitimate product and it is stated plainly here rather
> than dressed up: the category is full of tools claiming secret alpha, and a tool that tells you
> exactly which known premia you are buying, and proves it with a regression, is more defensible
> than the alternative. **The word 'alpha' does not appear in product copy.** The remaining edge
> is in construction, cost, tax and capacity — not in finding more signals."

### 1b. Pre-registered specification (fixed before running)

- **Primary object:** the headline's own series, `top − ew` = top-decile 63d return minus
  equal-weighted-universe 63d return, per rebalance date. `top_decile_alpha` is exactly
  `4 × mean(top − ew)`, so this is the number under audit and nothing else.
- **Secondary objects:** (i) top decile in excess of the risk-free rate — the long-only *book*, the
  thing a user actually holds; (ii) top-decile minus bottom-decile — the cleaner statistical object,
  per R1 method step 6.
- **Primary model:** `r_t = α + β₁MKT + β₂SMB + β₃HML + β₄RMW + β₅CMA + β₆UMD + ε`.
- **Secondary model:** Hou–Xue–Zhang q-factor — `MKT, ME, I/A, ROE` (q4, as the audit specifies).
  q5's `EG` reported as an appendix only; it is not the pre-registered model.
- **Inference:** Newey–West HAC, **lag 1**, as the audit specifies. Windows are adjacent and
  non-overlapping, but factor spreads are autocorrelated.
- **Aggregation:** daily factors compounded to the panel's own 63-trading-day windows, on the
  panel's own date grid, `(d_i, d_{i+1}]`. No look-ahead: every factor day used lies strictly
  inside the window whose return it is being matched to.
- **Robustness that will be reported whatever it says:** simple-sum aggregation instead of
  compounding, and the sample excluding the first 37 rebalance dates (audit **B6**: the panel's
  first third has an inverted universe). If the verdict differs between the pre-registered
  specification and either robustness cut, **the result is a null** — the pre-registered spec does
  not get to win a disagreement.

### 1c. Expected outcome, recorded in advance

Most of the +11.9% will not survive. RMW should absorb much of `quality` (the strongest theme),
SMB should absorb `size`, CMA should absorb `capital_discipline` (net issuance). What survives, if
anything, most likely comes from `institutional` and from the interaction structure of combining
seven themes.

---

## 2. Result — the threshold is cleared. **CLAIM A applies.**

**FF5+MOM intercept on the headline object: +8.81%/yr, Newey–West(1) t = +5.742.**
The pre-registered bar was "positive with t > 2.0". It passes on all four pre-registered
specifications, on both factor models, on all three objects, on every subperiod, at every
Newey–West lag from 0 to 8, net of the strategy's own trading costs, and after controlling for
the universe's own unexplained return. This was **not** the expected outcome — section 1c
predicted most of the 11.9% would be absorbed. Most of it was not.

Read the honest headline as a **range, not a point**: **+6.6% to +8.8%/yr** depending on whether
the B6-contaminated early period is included, and **+7.9%** net of costs on the full sample.

### 2a0. Disclosure — one deviation from the cold-session protocol

The prompt says to read X4 and X8 only *after* my own numbers are final. I complied with X8, but
**not fully with X4**: while locating the input series at the very start I opened
`ETF_BENCHMARK_RESULTS.json` and saw its verdict strings ("NULL — margin not demonstrated") and
its excess figures before running anything. Recorded rather than hidden.

Two reasons it does not contaminate the result. The pre-commitment in section 1 was written and
committed before *any* of my own numbers existed, so the threshold could not be moved. And X4's
finding is a **null**, so the direction of any bias it could have induced is toward expecting and
accepting a null — the opposite of what I found and reported. I did not read X8's numbers until
sections 2a–2f were written.

### 2a. What was run

```
python -m scripts.factor_alpha          # new file; touches no existing module
python tests/test_factor_alpha.py       # 14/14
```

- **Universe / series:** X4's shipped panel, `data/free_analysis/panel.pkl`, the full
  2,710-name universe. The script recomputes the top/ew series and **asserts it reproduces X4's
  shipped `ETF_BENCHMARK_RESULTS_strategy_series.csv` to 9.7e-17 on all 110 periods**, so this
  is measured on the same object the headline is, not a lookalike. `bot` (bottom decile) is the
  only column computed here that X4 did not already ship.
- **Weights:** the deployed `WEIGHTS_ESTABLISHED` — flat 0.125 across value, quality, momentum,
  insider, capital_discipline, size, institutional (`low_risk` zeroed, `sentiment` empty).
- **Dates:** 110 rebalance dates 1998-12-31 → 2026-04-22 give **109 non-overlapping 63-trading-day
  windows**, 1998-12-31 → 2026-01-21 (the last has no successor date). n = 109 for FF5+MOM;
  **n = 107** for the q models, because global-q's daily file stops at 2025-12-31 and two windows
  would be incomplete. Every window is exactly 63 factor days — verified, not assumed.
- **Factors:** D3's fetched and hash-verified files, already in decimals. No look-ahead is
  available in the construction: window *i* is `(d_i, d_{i+1}]` and `d_{i+1}` is literally the
  trading day on which the panel's own `fwd_ret` is realised.

### 2b. Alignment validation (the check that makes the rest believable)

The panel carries SPY's own 63-day return per date. Regressing SPY's excess return on MKT alone:

| | value |
|---|---|
| beta on MKT | **0.9562** |
| R² | **0.9888** |
| alpha | **+0.19%/yr (t +0.45)** |
| n | 72 (the panel has no benchmark before 2008 — audit B6) |

A large-cap ETF should load slightly *under* 1 on the total-market factor and show no alpha.
It does. A date-alignment or compounding error would have shown up here as a beta away from 1
and a collapsed R². This is asserted in the script, so it cannot silently regress.

### 2c. The regression tables — full sample, compounded windows (pre-registered primary)

**FF5+MOM** — `r_t = α + β₁MKT + β₂SMB + β₃HML + β₄RMW + β₅CMA + β₆UMD + ε`, NW lag 1.

| object | n | raw/yr | **α/yr** | **t(NW1)** | R² | MKT | SMB | HML | RMW | CMA | UMD |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| **top − ew** *(the headline)* | 109 | +12.13% | **+8.81%** | **+5.74** | 0.465 | +0.01 | **+0.39** | +0.11 | **+0.30** | +0.15 | **+0.18** |
| top − RF *(the book)* | 109 | +26.72% | +14.60% | +6.87 | 0.867 | **+1.07** | **+0.89** | +0.19 | +0.05 | +0.29 | +0.09 |
| long − short | 109 | +17.46% | +12.12% | +4.14 | 0.740 | **−0.38** | **+0.63** | **+0.45** | **+1.03** | **+0.49** | **+0.28** |
| EW universe − RF | 109 | +14.59% | +5.80% | +5.41 | 0.958 | **+1.07** | **+0.49** | +0.09 | **−0.25** | +0.14 | −0.09 |

Bold loadings are significant at |t| > 2. Full t-statistics on every loading are in
`data/free_analysis/FACTOR_ALPHA_RESULTS.json`.

**Hou–Xue–Zhang q4** (MKT, ME, I/A, ROE) — the harder test for a quality-heavy book:

| object | n | raw/yr | **α/yr** | **t(NW1)** | R² | MKT | ME | I/A | ROE |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| **top − ew** | 107 | +11.92% | **+9.14%** | **+5.23** | 0.421 | −0.03 | **+0.48** | +0.18 | **+0.37** |
| top − RF | 107 | +26.58% | +15.37% | +6.61 | 0.848 | **+1.02** | **+0.92** | **+0.33** | +0.03 |
| long − short | 107 | +17.00% | +12.99% | +3.20 | 0.666 | **−0.47** | **+0.98** | **+0.86** | **+1.00** |
| EW universe − RF | 107 | +14.65% | +6.23% | +5.75 | 0.958 | **+1.05** | **+0.45** | +0.15 | **−0.35** |

q4 does **not** kill it — the alpha is slightly *larger*. But q4 has **no momentum factor**, and
the composite loads +0.18 on UMD, so q4 is mechanically flattered here. **q5** (adding EG) gives
top − ew **+8.33%/yr, t +4.37**, which is the more comparable number. Either way, **FF5+MOM is
the pre-registered model and +8.81% / t 5.74 is the figure to quote.**

### 2d. The three headline figures side by side (method step 6)

| | top − ew | long − short |
|---|--:|--:|
| **raw excess return** | +12.13%/yr | +17.46%/yr |
| **FF5+MOM alpha** | **+8.81%/yr (t +5.74)** | **+12.12%/yr (t +4.14)** |
| **q-factor alpha (q4)** | **+9.14%/yr (t +5.23)** | **+12.99%/yr (t +3.20)** |

### 2e. Every robustness cut, including the two that could have vetoed the verdict

| cut | α/yr | t(NW1) | verdict |
|---|--:|--:|---|
| **compound / full** *(pre-registered primary)* | +8.81% | +5.74 | PASS |
| **compound / ex-B6 first 37** *(pre-registered veto cut)* | +6.58% | +4.41 | PASS |
| **sum aggregation / full** *(pre-registered veto cut)* | +8.70% | +5.57 | PASS |
| **sum / ex-B6 first 37** *(pre-registered veto cut)* | +6.30% | +4.27 | PASS |
| net of the strategy's own costs (drag 0.94%/yr, X4's formula) | +7.85% | +5.16 | — |
| **spanning test:** + the EW universe's own excess return as a 7th regressor | +8.25% | +5.88 | — |
| first half (1998-12 → 2012-04, n 54) | +8.98% | +3.38 | — |
| second half (2012-07 → 2026-01, n 55) | +5.48% | +3.12 | — |
| **2014+ (X4's window, n 49)** | **+6.06%** | **+3.16** | — |
| NW lag 0 / 2 / 4 / 8 | +8.81% | +6.31 / +5.42 / +5.09 / **+4.61** | — |

No cut fails. The pre-committed rule ("if the verdict differs between the pre-registered
specification and either robustness cut, the result is a null") is not triggered.

### 2f. Mechanism — what the factors *did* absorb, and what they did not

The pre-registered expectation was half right, and the half it got wrong is the interesting half.

- **Confirmed as expected.** `size` → **SMB +0.39 (t 3.84)**. `quality` → **RMW +0.30 (t 4.49)**.
  `momentum` → **UMD +0.18 (t 3.49)**. All three premia the composite was suspected of merely
  re-assembling are, in fact, present and statistically solid. The composite really is buying
  them, and the factor model really does explain a large share of its *variance* — R² 0.465 on
  a within-universe spread is high.
- **Refuted.** **HML +0.11 (t 1.08) and CMA +0.15 (t 1.08) are both insignificant.** The
  expectation that CMA would absorb `capital_discipline` (net issuance) and HML the `value`
  theme did not happen. Valquo's value theme is six ratios including EV-based and FCF-based
  ones, freshly re-priced at the rebalance date (P7/EV fix), which is not what HML measures;
  and `capital_discipline` is issuance-and-accruals, not FF's asset-growth-based investment
  factor. These two themes are contributing something the FF factors do not carry.
- **MKT loading on the spread is +0.007.** The headline is market-neutral by construction, as
  it should be — the equal-weighted universe benchmark strips beta out cleanly.
- **The arithmetic that shows this is not a benchmark artifact.** Alpha is linear, so
  α(top − ew) = α(top) − α(ew) = 14.60 − 5.80 = **8.81 exactly**. Whatever the factor model
  fails to price about this universe is *common to both legs and cancels*. The spanning test
  confirms it directly: adding the universe's own excess return as a seventh regressor gives it
  a loading of +0.10 (t 0.63, insignificant) and leaves alpha at +8.25% (t 5.88).
- **Where the raw +12.13% actually goes.** The OLS identity α = mean(y) − Σβᵢ·mean(fᵢ) splits
  the headline into the premium each factor is worth to this book. Reproduced by the script and
  asserted to agree with the fitted intercept to 1e-9:

  | factor | beta | × premium/yr | = contribution |
  |---|--:|--:|--:|
  | MKT | +0.007 | +8.12% | +0.05 pp |
  | SMB | +0.394 | +2.05% | +0.81 pp |
  | HML | +0.107 | +1.87% | +0.20 pp |
  | RMW | +0.298 | +3.80% | **+1.13 pp** |
  | CMA | +0.149 | +2.20% | +0.33 pp |
  | UMD | +0.181 | +4.45% | +0.80 pp |
  | **factor-explained total** | | | **+3.33 pp** |
  | **UNEXPLAINED (the alpha)** | | | **+8.81 pp** |

  **Of the raw 12.13 percentage points, 3.33 are the standard premia and 8.81 are not.** RMW is
  the single largest absorber at 1.13pp, exactly as predicted — it is just far smaller than the
  prediction implied. This is the clearest one-line statement of the R1 answer.
- **Most likely source, per the pre-registration:** `institutional` (no FF analogue), plus
  `value` and `capital_discipline` as *implemented here* rather than as FF measures them, plus
  the interaction structure of seven flat-weighted themes. R1 does not decompose this — an
  attribution regression per theme is the obvious follow-up and is not part of this item.

### 2g. Caveats. These are not optional and must travel with the number.

1. **This is still ONE panel.** A factor regression is a *control*, not new data. R1 raises the
   bar the result clears; it does not make it out-of-sample. **X8's international replication
   (Japan t 3.85, developed Europe t 4.30) is the out-of-sample evidence — R1 is not.**
2. **The t-statistic is not multiplicity-corrected.** The project's ledger holds ~146
   construction decisions (audit M1, still not done) and t 5.74 is not adjusted for any of them.
   Mitigating: **the deployed weights are flat 1/7 and were never tuned** — CPCV adopts no
   weighting over the defaults — so the *weights* are not fitted to this panel even though some
   theme-membership decisions were.
3. **FF5+MOM leaves +5.80%/yr (t 5.41) unexplained on the equal-weighted universe itself.**
   The factor model is a poor description of this universe — expected for an equal-weighted
   book with real small-cap weight, which SMB does not span well. It cancels out of the spread
   (2f), but every loading above should be read as approximate rather than precise.
4. **Small-cap tilt is real and unhedged.** The book loads SMB +0.885. Costs are charged
   (0.94%/yr, X4's own formula) but borrow, market impact at size, and capacity are not. Capacity
   is a separate audit item and this number says nothing about it.
5. **The B6 early period matters.** Dropping the first 37 contaminated dates costs about 2.2
   percentage points of alpha (+8.81% → +6.58%). Quote the range, and prefer +6.6% when a single
   conservative number is needed.
6. **`top − ew` is measured against an uninvestable benchmark** (equal-weighted 2,710 names,
   quarterly rebalanced). That is audit R10's problem, not solved here.

### 2h. Reconciling with X4 — they do not contradict each other

X4 found the strategy does not demonstrably beat a matched factor-ETF blend over 2014-2026
(t 1.10) or SPY (t 0.95). Over that **same** window R1 finds FF5+MOM alpha +6.06% with t 3.16.
Both are correct, because they are different tests:

- **X4 differences two high-variance total-return series.** Almost all of a stock portfolio's
  variance is market variance, so the standard error is enormous and even a +9.2pp annual gap
  only reaches t 1.10. It is a low-power test of a practical question.
- **R1 removes that variance before testing the mean.** Regressing away MKT/SMB/HML/RMW/CMA/UMD
  shrinks the residual standard error by roughly a factor of three, so a smaller number reaches
  a much larger t. It is a high-power test of a statistical question.
- They also use different benchmarks: X4's blend is four large-cap ETFs; R1's is the strategy's
  own universe.

**The synthesis across the three items is coherent:** X8 says the premia are real and general
(not US curve-fitting); **R1 says the headline is not only those premia — roughly 27% of the raw
+12.1% is factor exposure and the rest is not explained by FF5+MOM**; X4 says a retail user
cannot currently be shown to capture the residual with a cheap ETF substitute at conventional
significance. Alpha exists in the regression sense **and** the implementation margin remains
unproven in the practical sense. Both sentences are true simultaneously.

### 2i. Which pre-written claim now applies

**CLAIM A**, as written in section 1a before any number existed. Filled in:

> Valquo's top decile has produced returns that the standard five Fama–French factors plus
> momentum do not explain. After controlling for market, size, value, profitability, investment
> and momentum exposure, the model's selection adds an annualised intercept of **+8.8%
> (Newey–West t = 5.7)** over 1998–2026, **+6.6% (t 4.4)** excluding the contaminated early
> period, and **+7.9%** net of the model's own trading costs. That residual is what the model is
> actually for.

**The word "alpha" is permitted in product copy**, subject to two conditions that follow directly
from the caveats: quote it as a **range (+6.6% to +8.8%/yr)** or use the conservative +6.6%, and
never quote it without the fact that it is **measured on a single 27-year Sharadar panel with no
live track yet**. Claim B is retired for this item.

---

## 3. What I did NOT do

- **Did not touch the panel.** `fundamental_panel.py`, `factors.py`, `settings.py` and
  `screen.py` are untouched — Session 2 (B6/B7) owns them. Two new files and one new results
  JSON, nothing else.
- **Did not decompose the alpha by theme.** The claim that `institutional`, `value` and
  `capital_discipline` carry the residual is *inference from the loadings*, not a measurement.
- **Did not correct for the trial count.** Audit M1 is still open and this result inherits that.

## 3b. Incidental finding for the paper-track lane (not fixed — not my file)

`tests/test_paper_track.py` shows **3 failures when run locally on a developer machine and 0 in
CI**, on `main` as well as on this branch. Not a regression and not a landing blocker — branches
were still auto-merging to `main` at 05:35 today.

**Cause:** the three `test_hero_*` tests assert `live_hero(st)["index"]["source"] ==
"paper-sandbox"`, which is `hero.py`'s *fallback* branch. They build a paper-sandbox store but do
not isolate `valuation.screener.index_track.summarize()`, which on a real machine finds Don's
actual index track (`available: True`), so `live_hero` returns the **`index-track`** branch
instead and the assertion fails. In CI there is no such track, the fallback fires, and the tests
pass. Verified directly: `summarize(store=st)` returns `available=True` locally.

It should be isolated (stub `summarize` in those three tests) so local and CI agree — otherwise
every future session that runs the suites locally will see a red suite and waste time on it, as
this one did. **Left for whoever owns `paper_track` / the app-fixer lane.**

## 4. Recommended next step

The result changes the roadmap in the *opposite* direction from what R1 anticipated. The audit
said a null would make further signal hunting "close to worthless" and construction/cost/tax work
the entire remaining edge. A pass says the reverse: **there is a residual worth understanding.**

1. **Attribute the +8.81% across themes** — re-run this regression on each theme's own decile
   spread. It is cheap (the panel and the machinery now both exist) and it converts the inferred
   mechanism in 2f into a measured one. Highest value per hour in the project right now.
2. **M1, the append-only trial ledger.** t 5.74 is a large number that is not multiplicity-
   corrected, and this is now the single largest unquantified threat to the headline.
3. **The forward paper-track vs SPY stays the top priority overall** (CLAUDE.md item 12). R1
   raises the internal bar the model clears; it adds no out-of-sample evidence. → Cowork's lane.

## 5. Files

| file | status |
|---|---|
| `scripts/factor_alpha.py` | new — the R1 regressions, self-validating |
| `tests/test_factor_alpha.py` | new — 14 tests, all passing |
| `HANDOFF_r1.md` | new — this file |
| `data/free_analysis/FACTOR_ALPHA_RESULTS.json` | new output (gitignored with the rest of `data/`) |

Suites: **18 files run, all green except 3 pre-existing `test_paper_track.py` hero failures that
fail identically on `main` and belong to another lane.** `test_edge.py` 191/191.
