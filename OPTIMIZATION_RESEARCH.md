# Valquo — Deep Optimization Research: how to actually move the edge up

_July 2026. Grounded in the quant-finance literature (sources at bottom). Read the first section
before anything else — it reframes the whole question._

---

## 0. The core question: a "highest-peak" method instead of plugging in numbers?

Yes, those methods exist, and they split into two kinds:

- **Closed-form optimum.** For the objective "combine signals to maximize the information ratio,"
  the optimal weights have a *formula*: **w ∝ Σ⁻¹·μ** (inverse signal-covariance times signal
  returns — Markowitz / Grinold-Kahn). There is no grid; you solve it. **We already do this** — the
  `max-ir-decorr` scheme that keeps winning is exactly Σ⁻¹·μ with shrinkage. So for the linear
  weighting problem we are *already standing on the analytical peak*, not sampling a grid.
- **Continuous global optimizers** for objectives with no formula (e.g. the trade-parameter surface).
  **Bayesian optimization** (a Gaussian-process "surrogate" that models the whole performance surface
  and climbs to the global peak in ~20–50 evaluations, tolerant of noise), plus **CMA-ES** and
  **genetic algorithms**. These replace grids entirely and find the true peak, not grid corners.

### The catch that governs everything (this is the important part)
All of these find a higher peak **in-sample**. The proven, repeated result in quant finance is that
**the more configurations you search, the higher the chance the peak is noise**, and overfit
strategies *systematically underperform out-of-sample* (Bailey & López de Prado — "Probability of
Backtest Overfitting"; the Deflated Sharpe Ratio exists precisely to correct for this). The
out-of-sample performance surface is nearly **flat and drifts over time**, so a sharper peak-finder
usually *lowers* the real (OOS) result, not raises it. This is also why DeMiguel found naïve 1/N beats
"optimized" portfolios, and why we shrink, use purged walk-forward, and apply a trials haircut.

**Conclusion: the ceiling is the signal-to-noise of the data, not the search method.** A fancier
optimizer over the *same* signals will not move the OOS number up. What moves it up is below, roughly
in order of honest expected payoff.

---

## 1. Ranked levers to actually move up

### A. More / better *signal* (new data) — the biggest lever
Our IC is ~0.04. You don't beat that by re-weighting; you beat it by adding **orthogonal information**
the price/fundamental themes don't contain. Priorities (all currently missing or empty):
- **Analyst estimate *revisions* + dispersion** → fills our empty `sentiment` theme. One of the most
  robust public-market signals. (FMP, Intrinio.)
- **Short interest / days-to-cover / borrow cost** → a genuinely new theme; strong on the short side
  and for squeeze risk. (QuantQuote, ORTEX, FINRA bi-monthly.)
- **News/social sentiment** (retail buzz, NLP tone). (QuantQuote, ORTEX, Alpha Vantage.)
- **Options-implied** skew / put-call / IV term-structure — forward-looking, low correlation. (You
  already have Tradier live; historical is the gap for backtesting.)

### B. A non-linear model that extracts more from the signals we already have
Linear theme weights assume each signal acts independently and additively. **Gu, Kelly & Xiu (2020,
Review of Financial Studies)** show **boosted trees and neural nets roughly double** the
out-of-sample gains of linear factor models — *because* they capture **interactions** (e.g. "cheap
AND improving AND institutions accumulating" is worth more than the sum of the three). This is the
single most credible "new method." Caveats: it must be **heavily regularized** and validated with
purged CV, or it overfits spectacularly. Tooling: `lightgbm`/`xgboost` for gradient-boosted trees.

### C. Optimize the *right objective*
We currently tune weights for **IC** (rank correlation). But we care about **top-decile return** (or
risk-adjusted long-short, or the paper-account Sharpe). Optimizing the objective you actually want can
help more than a better optimizer of the wrong one. Cheap to test: swap the walk-forward's selection
metric from IC to top-decile alpha and re-run.

### D. Stronger *validation* so any gain is real, not luck
Upgrade our single-path walk-forward to **Combinatorial Purged Cross-Validation (CPCV)** — it builds
*many* train/test paths (not one), purges/embargoes overlaps, and yields a **lower Probability of
Backtest Overfitting** and a higher **Deflated Sharpe Ratio** than walk-forward or k-fold. Add the
**Deflated Sharpe Ratio** and **PBO** as headline numbers so we can *quantify* how likely a result is
overfit. Tooling: `skfolio` (CPCV), `mlfinlab` (López de Prado methods). This is the honest way to
tell whether an ML model or new signal is truly adding edge.

### E. Better weight optimization (marginal, but legitimate)
Full **mean-variance / IR maximization with Ledoit-Wolf covariance shrinkage** across signals (a more
principled version of what `max-ir-decorr` approximates); **Bayesian optimization / CMA-ES** for the
non-smooth trade-parameter surface (exit band, top_n, hold) instead of the current small grid — still
CPCV-gated. Expect small gains; these polish the peak, they don't create signal.

### F. Regime focus + portfolio construction (free, from what we already found)
- **Large-cap tilt** — our regime split showed the edge is *strongest in large caps* (IC ~0.046,
  long-short ~+8.6%/yr), not small. Focus the live book there.
- **De-concentrate** — top-decile book, not top-25 (top-25 loses; top-decile beats equal-weight).
- **Long-short / market-neutral** sleeve to harvest the ranking IC directly.

### G. Ensemble / stacking
Combine linear (max-ir-decorr) + tree + (later) NN into an ensemble; ensembles are usually more robust
OOS than any single model. Do this only after B and D exist.

---

## 2. Data sources to connect (fills the gaps in §1.A)

| Source | Adds | Fills theme | Access / cost (approx) |
|---|---|---|---|
| **Financial Modeling Prep (FMP)** | analyst estimates, price targets, revisions, grades | `sentiment` | cheap API, retail-friendly |
| **Intrinio** | historical analyst estimate *revisions* (point-in-time) | `sentiment` | mid, cleaner history |
| **QuantQuote** | FINRA short interest, days-to-cover, social sentiment, EPS | new `short_interest` | mid |
| **ORTEX** | short interest + ML composite score, full API, historical | new `short_interest` | mid, API-first |
| **Alpha Vantage** | news/social sentiment, fundamentals | `sentiment` | free tier + cheap |
| **FINRA (direct)** | bi-monthly short interest | new `short_interest` | free, but coarse cadence |

For a backtest, the key requirement is **point-in-time history** (as-of dates, no restatement) — FMP,
Intrinio and ORTEX can provide historical series; confirm as-of integrity before trusting a backtest.

---

## 3. Concrete build sequence (what I'd do, each OOS-gated)
1. **Upgrade validation first (CPCV + Deflated Sharpe + PBO).** Without this we can't trust anything
   below. Also re-express the current result with a DSR/PBO so we know how overfit today's edge is.
2. **Validate the institutional 39%** — re-run with it removed/capped; see how much edge depends on
   lagged 13F data. (Due diligence before any live money.)
3. **Add the sentiment theme for real** via analyst estimate revisions (FMP/Intrinio) — the clearest
   missing orthogonal signal.
4. **Add a short-interest theme** (QuantQuote/ORTEX).
5. **Train a regularized gradient-boosted-tree combiner** on all themes; compare its CPCV Deflated
   Sharpe to the linear max-ir-decorr. Keep whichever wins honestly; ensemble if close.
6. **Switch the objective** to top-decile / risk-adjusted and re-check.
7. **Large-cap-tilted, de-concentrated construction** for the live book.

---

## 4. Honest expectation
Public-market cross-sectional signals top out around IC ~0.03–0.06; the pros live there too. Realistic
upside from all of the above is a **modestly stronger, better-validated tilt** — not a step-change to a
market-neutral money machine. The step-changes in this business come from **data others don't have**
and **execution/patience**, not from a cleverer optimizer. The live track record remains the only proof
that survives scrutiny.

---

## Sources
- Bailey & López de Prado, *The Deflated Sharpe Ratio* — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- Bailey, Borwein, López de Prado, Zhu, *The Probability of Backtest Overfitting* — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
- Gu, Kelly & Xiu, *Empirical Asset Pricing via Machine Learning* (RFS 2020) — https://academic.oup.com/rfs/article/33/5/2223/5758276
- *Purged / Combinatorial Purged Cross-Validation* — https://en.wikipedia.org/wiki/Purged_cross-validation ; https://blog.quantinsti.com/cross-validation-embargo-purging-combinatorial/
- skfolio (CPCV, portfolio optimization in Python) — https://skfolio.org/generated/skfolio.model_selection.CombinatorialPurgedCV.html
- Bayesian optimization overview — https://arxiv.org/pdf/2003.05689
- Signal combination (IR optimization + covariance shrinkage) — https://insight.factset.com/a-practical-approach-to-weighting-signals ; https://arxiv.org/pdf/1603.05937
- Data vendors — FMP: https://site.financialmodelingprep.com/datasets/analyst-estimates-targets ; ORTEX: https://public.ortex.com/ ; QuantQuote short interest: https://www.quantquote.com/data/short-interest/
