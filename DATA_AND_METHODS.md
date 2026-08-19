# Data & Methods — how to actually prove (or disprove) an edge

Short version: **the data is where edges are won or lost, and most "edges" are
statistical illusions.** Free feeds (yfinance/Stooq) are fine for a live product
but wrong for research — they drop delisted losers (survivorship bias) and carry
no point-in-time fundamentals, so they *manufacture* fake edge. To find a real one
you need survivorship-free, point-in-time data plus a protocol built to reject
flukes. Here's the whole picture.

---

## 1. The data you actually need
Three properties, in order of importance:

1. **Survivorship-bias-free with delisting returns.** Include companies that went
   to zero, got acquired, or delisted — *with the terminal return*. Omitting them
   is the single biggest source of fake backtest edge.
2. **Point-in-time fundamentals ("as reported, as known on the date").** Use the
   numbers as they were filed on each historical date, not today's restated values.
   (Valquo's panel does this from Sharadar SF1 filing dates; the sibling
   [equity factor screener](https://github.com/dcorbin07/stock_screener) reconstructs it from
   EDGAR filing dates.)
3. **Historical index membership + corporate-action-adjusted prices** (splits,
   dividends, spin-offs).

### What this project uses, and what the alternatives are

**Valquo's research panel is built from Sharadar (via Nasdaq Data Link)** — SF1 point-in-time
fundamentals, ~21k active *and delisted* tickers back to 1998, plus corporate actions and
insider filings. All three properties above are satisfied by it, which is why the backtest is
able to make a claim at all.

> **Licence limit, and it binds anyone reproducing this work.** Sharadar's terms are
> **personal-use only and forbid commercial use of the data "or any derivation"**. The exports
> are gitignored and never published in this repository. A stranger can rebuild the panel only
> under their own licence — and that licence would not let them publish what they derived.

| Alternative | What it gives | Rough cost | Notes |
|---|---|---|---|
| **CRSP + Compustat via WRDS** | The academic gold standard: survivorship-free prices with delisting returns + point-in-time fundamentals | Free through many university business programs | Best available if you have institutional access |
| **Sharadar (Nasdaq Data Link)** | *what this project uses* — see above | tens of $/mo | The standard affordable "institutional-quality" retail choice |
| **Norgate Data** | Survivorship-free US prices incl. delisted, historical index constituents | ~$ tens/mo | Strong for price/technical backtests |
| **EODHD** | Fundamentals feed | ~€60/mo | Cheaper; verify point-in-time quality before trusting factor tests |
| **Tiingo** | Prices + some fundamentals | free tier / <$30/mo | Budget option; lighter PIT coverage |

There is **no credible free survivorship-free fundamentals source.** The free stack the live
product runs on (Yahoo, EDGAR, Stooq) is fine for serving a page and wrong for research.

---

## 2. The methods that are actually reputable and repeatable
The academic record is humbling, and you should internalize it:

- **Most published anomalies don't replicate.** Hou, Xue & Zhang, *Replicating
  Anomalies* (2020): under proper methods the large majority of ~450 anomalies are
  insignificant. Harvey, Liu & Zhu (2016): a genuinely new factor needs a
  **t-statistic > 3** (not 2) to survive multiple testing; 27–53% of published
  factors are likely false discoveries.
- **Edges decay after publication.** McLean & Pontiff (2016): factor returns fall
  ~30–58% out-of-sample once a strategy is known (arbitrage + overfitting).

So don't chase exotic signals. Lean on the **handful of factors with the strongest,
most-replicated evidence**, which are also the ones the tool already uses:

- **Value** (cheapness), **Momentum** (12-1 month; Jegadeesh-Titman, Carhart),
  **Quality/Profitability** (Novy-Marx gross profitability; AQR "Quality Minus
  Junk"), **Investment/asset-growth**, **Low-risk / betting-against-beta**, and
  weakly **Size**. These anchor the Fama-French 5-factor and Hou-Xue-Zhang q-factor
  models. That is the "reputable and repeatable" toolkit — resist adding more.

---

## 3. The protocol (this is what makes a result trustworthy)
1. **Survivorship-free + point-in-time data** (§1). Everything else is secondary.
2. **Include delisting returns** (set delisted-to-zero where appropriate).
3. **Realistic costs + slippage + turnover control** (we subtract round-trip costs;
   tighten to match your own broker).
4. **Cross-sectional standardized factors → IC + quantile spread** (we do this).
5. **Walk-forward / expanding-window out-of-sample** — never a single in-sample fit
   (the Edge Lab does this).
6. **Multiple-testing correction** — the part most people skip:
   - **The Harvey-Liu-Zhu hurdle** for "new" factors (`edge/statistics.hlz_significant`).
     It is **√(2·ln N)**, NOT the constant 3.0 often quoted — see §4, and note it RISES
     with every trial you charge.
   - **Deflated Sharpe Ratio** (Bailey & López de Prado): deflates a backtest Sharpe
     for the *number of variants you tried*, sample length, skew and kurtosis, and
     returns the probability the edge is real. **Now built in** — the Edge Lab's
     `optimize` reports it. On the shipped panel it reads **0.79** against a >0.95
     convention. This is the single best guard against fooling yourself.
7. **Confirm out-of-sample and forward.** The live track record (survivorship-free
   going forward) is the ultimate arbiter.

---

## 4. What is built (this section used to be a to-do list)
**Built (reputable, working today):** cross-sectional z-scores, IC, quantile spread
after costs, walk-forward optimization, sample-awareness, the Claude advisor judged
on a holdout, and now the **Deflated Sharpe Ratio + the Harvey–Liu–Zhu hurdle**. (CORRECTED
2026-08-15, audit `MA5`: this read "HLZ t>3 gate". The bar is **√(2·ln N)**, not a constant —
3.0 is that expression at N = 90 and this project passed N = 90 on 2026-08-06. At today's
equity N = 224 the hurdle is **3.2899** and it rises with every trial. Quoting "t>3" states
a bar the project cleared under a denominator it no longer has.) The price-factor
(momentum/technical) research runs on free data now.

**ALL THREE ITEMS THIS SECTION USED TO LIST AS "to add" HAVE SINCE BEEN BUILT** (corrected
2026-08-16, public-accuracy pass — the list below described the project as it stood before the
Sharadar panel existed, and read as though the research had never been done):

- **The survivorship-free data adapter** ships as `valuation/edge/data_providers.py` +
  `bulk.py`, consuming the Sharadar exports.
- **Point-in-time fundamentals** are the panel's basis —
  `valuation/edge/fundamental_panel.py::build_fundamental_panel()` builds all nine themes
  point-in-time and reuses the live `build_frame`, so the research and live paths score
  identically (pinned by test).
- **Delisting-return handling** is in place via the corporate-actions mask, so names that went
  to zero, were acquired or were delisted carry their terminal return.

The panel runs **2,531 names over 69 quarterly rebalances (2009–2026)**.

---

## The honest bottom line
With good data and this protocol you get a *trustworthy* answer — which may well be "no reliable
edge after costs". That is not a failure; it is the point. **On this project it is largely what
happened:** the overwhelming majority of pre-registered tests came back NULL or REJECTED, and the
one surviving claim clears its own placebo-calibrated floor while failing the stricter hurdle
implied by counting every trial charged. Both halves ship in `BACKTEST_RESULTS.json`.

The tooling is built to find an edge if one exists and to say plainly when it does not, so that
nobody bets real money on a curve fit.

*Educational tooling and research methodology — not investment advice.*

### Sources
- Bailey & López de Prado, "The Deflated Sharpe Ratio" (SSRN 2460551).
- Harvey, Liu & Zhu (2016), "…and the Cross-Section of Expected Returns."
- Hou, Xue & Zhang (2020), "Replicating Anomalies" (NBER w23394).
- McLean & Pontiff (2016), out-of-sample decay of predictors.
- Sharadar / Nasdaq Data Link; Norgate Data; CRSP; EODHD; Tiingo (data vendors).
